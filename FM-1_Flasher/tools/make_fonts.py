#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 John Park for Adafruit Industries
#
# SPDX-License-Identifier: GPL-3.0-only
"""Render TrueType fonts into the packed 1-bit fonts (.fmf) the device UI uses.

  tools/make_fonts.py --inter Inter.ttf --mono JetBrainsMono.ttf --out fonts/

Inter (the Firmware Hub's font) and JetBrains Mono are OFL-licensed; get the
variable TTFs from github.com/google/fonts (ofl/inter, ofl/jetbrainsmono).

An .fmf keeps every glyph in one 1-bit sheet, so the device holds a font in
a single Bitmap (a few KB) instead of one Bitmap and Glyph object per
character, and draws text with bitmaptools.blit. Layout, little-endian:

  b"FMF1", u8 ascent, u8 descent, u8 cap height, u8 0,
  u16 glyph count, u16 sheet width (a multiple of 8)
  per glyph: u16 code point, u16 x in sheet, u8 width, i8 left bearing,
             u8 advance, u8 0                        (printable ASCII first,
                                                      in order, from 32)
  the sheet: ascent + descent rows, MSB-first 1-bit pixels, rows padded to bytes

Row 0 of the sheet is `ascent` pixels above the baseline. Glyphs are
rendered without anti-aliasing.
"""

import argparse
import os
import struct

from PIL import Image, ImageDraw, ImageFont

# (file name, source, weight, pixel size, with EXTRA). The title and mono
# fonts are ASCII only, to save the device's RAM: the catalog's names,
# versions and identities are ASCII, and the UI sets a title that isn't in
# the 14 px bold font (fm1ui.ui.title_font).
FONTS = (
    ("inter-bold-14.fmf", "inter", b"Bold", 14, True),
    ("inter-bold-22.fmf", "inter", b"Bold", 22, False),
    ("inter-regular-14.fmf", "inter", b"Regular", 14, True),
    ("mono-bold-12.fmf", "mono", b"Bold", 12, False),
)

# Beyond ASCII: Latin-1 letters and the Latin Extended-A letters of the
# languages in the hub's catalog and nearby ones, and common punctuation.
EXTRA = ("ÀÁÂÃÄÅÆÇÈÉÊËÌÍÎÏÐÑÒÓÔÕÖØÙÚÛÜÝÞßàáâãäåæçèéêëìíîïðñòóôõöøùúûüýþÿ"
         "ĀāĆćČčĎďĒēĚěĞğĪīİıŁłŃńŇňŌōŐőŒœŘřŚśŞşŠšŤťŪūŮůŰűŸŹźŻżŽž"
         "–—‘’“”•…·°×©®™←→")


_LEAD = "H "  # a capital, then an em space so it can't touch the glyph


def _render(font, s, w, h, x, baseline):
    img = Image.new("1", (w, h))
    d = ImageDraw.Draw(img)
    d.fontmode = "1"
    d.text((x, baseline), s, font=font, fill=1, anchor="ls")
    return img


def _draw(font, ch, size, baseline):
    """The glyph alone, at its height in running text. Drawn by itself, Pillow
    puts a few glyphs a pixel high (Inter Bold's r, < and >), so its rows come
    from a render after _LEAD, where it sits on the same baseline as text."""
    h = baseline + size * 2
    img = _render(font, ch, size * 4, h, size, baseline)
    box = img.getbbox()
    if box is None:
        return img
    lead = _render(font, _LEAD, size * 8, h, size, baseline).getbbox()[2] + 1
    ctx = _render(font, _LEAD + ch, size * 8, h, size, baseline).crop((lead, 0, size * 8, h)).getbbox()
    dy = ctx[1] - box[1] if ctx else 0
    if dy:
        moved = Image.new("1", img.size)
        moved.paste(img, (0, dy))
        img = moved
    return img


def write_fmf(path, ttf, weight, size, extra=True):
    font = ImageFont.truetype(ttf, size)
    font.set_variation_by_name(weight)
    base = size * 2
    chars = [chr(c) for c in range(32, 127)]
    drawn = {}
    for ch in chars + list(EXTRA if extra else ""):
        img = _draw(font, ch, size, base)
        if ch in chars or img.getbbox():  # skip what the font doesn't have
            drawn[ch] = (img, img.getbbox())
    chars = list(drawn)
    # The line box is the real ink extent, accents and descenders included.
    ascent = max(base - b[1] for _, b in drawn.values() if b)
    descent = max(b[3] - base for _, b in drawn.values() if b)
    cap = base - drawn["H"][1][1]
    h = ascent + descent

    glyphs = []
    for ch in chars:
        img, box = drawn[ch]
        adv = round(font.getlength(ch))
        if box is None:
            glyphs.append((ch, None, 0, 0, adv))
            continue
        x0, x1 = box[0], box[2]
        glyphs.append((ch, img.crop((x0, base - ascent, x1, base + descent)), x0 - size, x1 - x0, adv))

    sheet_w = (sum(g[3] for g in glyphs) + 7) // 8 * 8
    sheet = Image.new("1", (sheet_w, h))
    table = b""
    x = 0
    for ch, img, left, w, adv in glyphs:
        if img is not None:
            sheet.paste(img, (x, 0))
        table += struct.pack("<HHBbBB", ord(ch), x, w, left, adv, 0)
        x += w
    with open(path, "wb") as f:
        f.write(b"FMF1" + struct.pack("<BBBBHH", ascent, descent, cap, 0, len(glyphs), sheet_w))
        f.write(table)
        f.write(sheet.tobytes())  # mode "1": MSB first, rows padded to bytes
    return len(glyphs), sheet_w, h


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--inter", required=True)
    ap.add_argument("--mono", required=True)
    ap.add_argument("--out", default="FM-1_Flasher_Code/fonts")
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)
    for name, src, weight, size, extra in FONTS:
        n, w, h = write_fmf(os.path.join(args.out, name), getattr(args, src), weight, size, extra)
        print("%-22s %3d glyphs, sheet %dx%d (%d bytes)" % (name, n, w, h, w * h // 8))


if __name__ == "__main__":
    main()
