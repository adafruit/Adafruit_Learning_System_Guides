#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 John Park for Adafruit Industries
#
# SPDX-License-Identifier: GPL-3.0-only
"""Prepare firmware folders for the flasher's microSD card.

Each firmware becomes  <out>/firmware/<slug>/<product>.fwsc + meta.json,
fully verified with the same checks the device runs (fm1proto.prepare).

Sources:
  --html Update.html     an FM1 Open-style release page; its embedded
                         FM1_PACKAGE JSON carries the package and metadata
  --fwsc FILE --meta M   a package plus a JSON file of metadata fields
  --fwsc FILE            stock V15 is recognized by its SHA-256, FM-1_<n>
                         packages install by the community route; FM1 Open
                         packages need --build-id
  --catalog [ID ...]     download from the FM-1 Firmware Hub catalog
                         (all firmwares plus stock V15, or only the given
                         ids), verifying each package's SHA-256 against the
                         catalog, with the hub's card pictures as
                         thumb.bmp/large.bmp (needs Pillow). Packages already
                         on the card are reused when their SHA-256 matches.
                         Firmwares the hub sends to their own installer
                         (an `install` link: they write data the package
                         doesn't carry) are left out. Nothing already on the
                         card is ever removed: a firmware the hub drops or
                         moves to its own installer stays until you delete
                         its folder.

Every run rewrites firmware/index.txt, the list the device's UI reads.

Examples:
  tools/make_sd.py --out /Volumes/FM1SD --fwsc ref/fm1_open/sdk/firmware/FM-1_015.fwsc \\
      --name "M-VAVE V15 (stock)" --author M-VAVE --license Apache-2.0
  tools/make_sd.py --out /Volumes/FM1SD --html ~/Downloads/Update.html --source-url https://...
  tools/make_sd.py --out /Volumes/FM1SD --catalog sloop felucca
"""

import argparse
import base64
import hashlib
import io
import json
import os
import re
import sys
import urllib.request

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "FM-1_Flasher_Code", "lib"))
import fm1catalog as K  # noqa: E402
import fm1proto as P  # noqa: E402

FIELDS = ("schema", "kind", "product", "family", "build_id", "bytes", "sha256", "loader_sha256",
          "release_version", "profile")
EXTRA = ("name", "author", "version", "source_url", "license", "notes")
HUB = K.HUB
UA = {"User-Agent": "FM-1_Flasher make_sd.py"}


def fetch(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r:
        return r.read()


own_installer = K.own_installer


def catalog_entries(cat, ids):
    """The catalog's firmwares (all, or only `ids`), with stock V15 first.
    Firmwares with their own installer are left out."""
    try:
        return K.entries(cat, ids or None)
    except KeyError as e:
        sys.exit("not in the catalog, no package, or installs from its own page: " + e.args[0])


def local_package(out, e):
    """The package already on the card for catalog entry `e`, if it matches."""
    d = os.path.join(out, "firmware", e["id"])
    try:
        meta = json.load(open(os.path.join(d, "meta.json")))
        if meta.get("sha256") == e["sha256"]:
            return open(os.path.join(d, meta["file"]), "rb").read()
    except (OSError, ValueError, KeyError):
        pass
    return None


def from_catalog(ids, out):
    cat = json.loads(fetch(HUB + "catalog.json"))
    result = []
    for e in catalog_entries(cat, ids):
        data = local_package(out, e)
        if data is None:
            data = fetch(HUB + e["pkg"])
        if hashlib.sha256(data).hexdigest() != e["sha256"] or len(data) != e["size"]:
            print("skipping %s: download does not match the catalog" % e["id"], file=sys.stderr)
            continue
        meta = K.meta_for(e)
        result.append((data, meta, e["id"]))
    return result, cat.get("updated")


def thumbnails(d, cid):
    """thumb.bmp (80 px) and large.bmp (160 px) from the hub's card picture,
    as 8-bit indexed BMPs of 16 colors. The device reads them into a fixed
    pool of 80x80 bitmaps (fm1ui.ui.slots), so large.bmp is stored as its four
    80 px quarters stacked top to bottom (top left, top right, bottom left,
    bottom right): an 80x320 strip. The pictures are mostly 480 px pixel art,
    so 6x and 3x nearest-neighbor shrinks stay sharp."""
    try:
        from PIL import Image
    except ImportError:
        print("no Pillow: skipping thumbnails", file=sys.stderr)
        return
    try:
        img = Image.open(io.BytesIO(fetch(HUB + "img/%s.png" % cid))).convert("RGB")
    except Exception as e:  # no picture, or not an image
        print("%s: no thumbnail (%s)" % (cid, e), file=sys.stderr)
        return
    side = max(img.size)
    square = Image.new("RGB", (side, side), (0x0E, 0x0C, 0x0D))
    square.paste(img, ((side - img.width) // 2, (side - img.height) // 2))
    for name, px in (("thumb.bmp", 80), ("large.bmp", 160)):
        resample = Image.NEAREST if side % px == 0 else Image.LANCZOS
        small = square.resize((px, px), resample).quantize(16)
        if px > 80:
            strip = Image.new("P", (80, px * px // 80))
            strip.putpalette(small.getpalette())
            for i in range(px * px // 6400):
                tx, ty = (i % (px // 80)) * 80, (i // (px // 80)) * 80
                strip.paste(small.crop((tx, ty, tx + 80, ty + 80)), (0, 80 * i))
            small = strip
        small.save(os.path.join(d, name))


def write_index(out, updated=None):
    """firmware/index.txt, from the card's meta.json files (fm1catalog)."""
    return K.write_index(os.path.join(out, "firmware"), updated)


def from_html(path):
    text = open(path, encoding="utf-8", errors="replace").read()
    m = re.search(r"const FM1_PACKAGE = (\{.*?\});", text, re.S)
    if not m or m.group(1) == "null":
        sys.exit("%s: no embedded FM1_PACKAGE" % path)
    pkg = json.loads(m.group(1))
    out = []
    for meta in (pkg, pkg.get("stock")):
        if not meta:
            continue
        data = base64.b64decode(meta["data"])
        meta = {k: v for k, v in meta.items() if k not in ("data", "stock")}
        out.append((data, meta))
    return out


def slugify(s):
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-") or "firmware"


def build(data, meta, args):
    meta = dict(meta)
    for k in EXTRA:
        v = getattr(args, k.replace("-", "_"), None)
        if v:
            meta[k] = v
    try:
        return K.finish(meta, io.BytesIO(data))
    except P.FM1Error as e:
        if "build_id unknown" in str(e):
            sys.exit(str(e))
        raise


def write(out, data, meta, slug=None):
    slug = slug or slugify(meta["name"] + "-" + meta.get("release_version", meta["sha256"][:8]))
    d = os.path.join(out, "firmware", slug)
    os.makedirs(d, exist_ok=True)
    meta.setdefault("file", meta["product"] + ".fwsc")
    with open(os.path.join(d, meta["file"]), "wb") as f:
        f.write(data)
    with open(os.path.join(d, "meta.json"), "w") as f:
        json.dump(meta, f, indent=1, sort_keys=True)
        f.write("\n")
    return d


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", required=True, help="SD card root (or a staging folder)")
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--html", help="release Update.html with an embedded FM1_PACKAGE")
    src.add_argument("--fwsc", help="a .fwsc package")
    src.add_argument("--catalog", nargs="*", metavar="ID", help="FM-1 Firmware Hub catalog ids (none: all)")
    ap.add_argument("--meta", help="JSON file with metadata fields for --fwsc")
    ap.add_argument("--build-id", help="64-hex build identity for --fwsc")
    ap.add_argument("--slug", help="folder name under firmware/")
    ap.add_argument("--no-stock", action="store_true", help="with --html, skip the bundled V15")
    ap.add_argument("--no-thumbnails", action="store_true", help="with --catalog, skip the card pictures")
    for k in EXTRA:
        ap.add_argument("--" + k.replace("_", "-"))
    args = ap.parse_args(argv)

    slugs = {}
    updated = None
    if args.catalog is not None:
        items = []
        found, updated = from_catalog(args.catalog, args.out)
        for data, meta, cid in found:
            items.append((data, meta))
            slugs[id(meta)] = cid
    elif args.html:
        items = from_html(args.html)
        if args.no_stock:
            items = [i for i in items if i[1].get("kind") != "stock"]
    else:
        data = open(args.fwsc, "rb").read()
        meta = json.load(open(args.meta)) if args.meta else {}
        if args.build_id:
            meta["build_id"] = args.build_id.lower()
        items = [(data, meta)]

    failed = 0
    for data, meta in items:
        slug = slugs.get(id(meta)) or (args.slug if len(items) == 1 else None)
        try:
            meta = build(data, meta, args)
        except P.FM1Error as e:
            print("rejected %s: %s" % (meta.get("product") or meta.get("name"), e), file=sys.stderr)
            failed += 1
            continue
        d = write(args.out, data, meta, slug)
        if meta.get("catalog_id") and not args.no_thumbnails:
            thumbnails(d, meta["catalog_id"])
        print("%-20s %-12s %7d bytes  loader %s  -> %s" % (
            meta["product"], meta["kind"], meta["bytes"], meta["loader_identity"], d))
    print("index: %d firmwares" % write_index(args.out, updated))
    if failed:
        sys.exit("%d package(s) rejected" % failed)


if __name__ == "__main__":
    main()
