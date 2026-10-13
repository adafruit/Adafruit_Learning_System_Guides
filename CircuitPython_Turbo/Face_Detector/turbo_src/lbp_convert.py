# SPDX-FileCopyrightText: 2026 Liz Clark for Adafruit Industries
#
# SPDX-License-Identifier: MIT
"""Convert an OpenCV LBP cascade (XML) into a compact binary for CircuitPython.

To run::

    python lbp_convert.py lbpcascade_frontalface.xml frontalface.lbp

The binary is a flat run of little-endian signed 32-bit words, so the board
can read it straight into an ``array.array("i")`` with ``readinto()`` and a
Viper module can use it as a ``ptr32``. 

====== =============================================================
words  contents
====== =============================================================
0      magic: the bytes ``LBPC``
1      format version (1)
2-3    detection window width, height in pixels
4      stage count
5      weak classifier count, all stages together
6      feature count
7      fixed-point shift
8-15   reserved, 0
then   3 words per stage: first weak classifier, weak count, threshold
then   11 words per weak classifier: feature index, 8-word category
       mask, leaf added when the LBP code's bit is set, leaf when clear
then   4 words per feature: x, y, block width, block height
====== =============================================================
"""

import argparse
import re
import struct
import sys
import xml.etree.ElementTree as ET

MAGIC = struct.unpack("<i", b"LBPC")[0]
VERSION = 1
HEADER_WORDS = 16
STAGE_WORDS = 3
WEAK_WORDS = 11
FEATURE_WORDS = 4
# OpenCV subtracts this from every stage threshold when it loads a cascade.
THRESHOLD_EPS = 1e-5
INT32_MIN, INT32_MAX = -(2**31), 2**31 - 1


class CascadeError(ValueError):
    """If the XML isn't a cascade this converter can handle."""

def _text(node, tag):
    child = node.find(tag)
    if child is None or child.text is None:
        raise CascadeError("missing <%s>" % tag)
    return child.text.strip()

def _items(node, tag):
    child = node.find(tag)
    if child is None:
        raise CascadeError("missing <%s>" % tag)
    return child.findall("_")

def parse_cascade(path):
    """Read an LBP cascade XML into plain Python numbers."""
    with open(path, "rb") as file:
        raw = file.read()
    text = raw.decode("utf-8", errors="replace")
    match = re.match(r"\s*(?:<\?xml[^>]*\?>\s*)?<!--(.*?)-->", text, re.S)
    notice = match.group(1).replace("\r", "").strip("\n") if match else ""

    root = ET.fromstring(raw)
    cascade = root.find("cascade")
    if cascade is None:
        raise CascadeError(
            "no <cascade>: this looks like an old-format cascade; only the "
            "opencv_traincascade format is supported"
        )
    feature_type = _text(cascade, "featureType")
    if feature_type != "LBP":
        raise CascadeError("featureType is %s; only LBP is supported" % feature_type)
    if _text(cascade, "stageType") != "BOOST":
        raise CascadeError("only BOOST stages are supported")
    params = cascade.find("stageParams")
    if params is not None and params.find("maxDepth") is not None:
        if int(_text(params, "maxDepth")) != 1:
            raise CascadeError("only depth-1 weak classifiers (stumps) are supported")
    width = int(_text(cascade, "width"))
    height = int(_text(cascade, "height"))

    features = []
    for item in _items(cascade, "features"):
        values = [int(v) for v in _text(item, "rect").split()]
        if len(values) != 4:
            raise CascadeError("an LBP feature rect needs 4 numbers")
        x, y, w, h = values
        # The feature is a 3x3 grid of w x h blocks and must fit the window.
        if w < 1 or h < 1 or x < 0 or y < 0 or x + 3 * w > width or y + 3 * h > height:
            raise CascadeError("feature %d %r is outside the window" % (len(features), values))
        features.append((x, y, w, h))

    stages = []
    for stage in _items(cascade, "stages"):
        threshold = float(_text(stage, "stageThreshold"))
        weaks = []
        for weak in _items(stage, "weakClassifiers"):
            nodes = [int(v) for v in _text(weak, "internalNodes").split()]
            leaves = [float(v) for v in _text(weak, "leafValues").split()]
            # A stump: left = 0, right = -1 (both leaves), the feature, then
            # the 256-bit category mask as 8 signed 32-bit words.
            if len(nodes) != 11 or nodes[0] != 0 or nodes[1] != -1 or len(leaves) != 2:
                raise CascadeError("weak classifier is not a categorical stump")
            feature = nodes[2]
            if not 0 <= feature < len(features):
                raise CascadeError("feature index %d out of range" % feature)
            weaks.append((feature, nodes[3:11], leaves[0], leaves[1]))
        if not weaks:
            raise CascadeError("stage %d has no weak classifiers" % len(stages))
        stages.append((threshold, weaks))
    if not stages:
        raise CascadeError("no stages")
    return {
        "width": width,
        "height": height,
        "stages": stages,
        "features": features,
        "notice": notice,
    }

def _fixed(value, shift):
    result = int(round(value * (1 << shift)))
    if not INT32_MIN <= result <= INT32_MAX:
        raise CascadeError("%r doesn't fit 32 bits at shift %d" % (value, shift))
    return result

def to_words(cascade, shift=20):
    """The binary layout as a list of ints."""
    stages = cascade["stages"]
    features = cascade["features"]
    weak_count = sum(len(weaks) for _, weaks in stages)
    words = [0] * HEADER_WORDS
    words[0:8] = [
        MAGIC,
        VERSION,
        cascade["width"],
        cascade["height"],
        len(stages),
        weak_count,
        len(features),
        shift,
    ]
    first = 0
    largest = 0
    for threshold, weaks in stages:
        words += [first, len(weaks), _fixed(threshold - THRESHOLD_EPS, shift)]
        first += len(weaks)
        largest = max(largest, sum(max(abs(a), abs(b)) for _, _, a, b in weaks))
    # The kernel adds up to one stage's leaves; make sure that can't wrap.
    if largest * (1 << shift) >= 2**30:
        raise CascadeError("a stage's leaf sum could overflow at shift %d" % shift)
    for _, weaks in stages:
        for feature, mask, leaf_set, leaf_clear in weaks:
            words.append(feature)
            words += mask
            words += [_fixed(leaf_set, shift), _fixed(leaf_clear, shift)]
    for feature in features:
        words += list(feature)
    return words

def write_binary(words, path):
    with open(path, "wb") as file:
        file.write(struct.pack("<%di" % len(words), *words))

def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("xml", help="OpenCV LBP cascade, e.g. lbpcascade_frontalface.xml")
    parser.add_argument("output", help="binary to write, e.g. frontalface.lbp")
    parser.add_argument(
        "--shift",
        type=int,
        default=20,
        help="fixed-point bits after the binary point (default 20)",
    )
    args = parser.parse_args(argv)
    try:
        cascade = parse_cascade(args.xml)
        words = to_words(cascade, args.shift)
    except (CascadeError, ET.ParseError) as error:
        sys.exit("%s: %s" % (args.xml, error))
    write_binary(words, args.output)

    weak_counts = [len(weaks) for _, weaks in cascade["stages"]]
    print(
        "%s: %dx%d window, %d stages, %d weak classifiers, %d features"
        % (
            args.xml,
            cascade["width"],
            cascade["height"],
            len(weak_counts),
            sum(weak_counts),
            len(cascade["features"]),
        )
    )
    print("weak classifiers per stage:", " ".join(str(n) for n in weak_counts))
    print("wrote %s: %d bytes (shift %d)" % (args.output, 4 * len(words), args.shift))
    notice_path = args.output + ".NOTICE.txt"
    with open(notice_path, "w") as file:
        file.write("Converted by lbp_convert.py from %s\n" % args.xml)
        file.write("Keep this notice with the converted cascade.\n\n")
        if cascade["notice"]:
            file.write(cascade["notice"] + "\n")
        else:
            file.write("(The source XML carried no comment header.)\n")
    print("wrote %s" % notice_path)

if __name__ == "__main__":
    main()
