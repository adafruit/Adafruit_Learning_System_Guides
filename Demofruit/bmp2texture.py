#!/usr/bin/env python3
"""Convert a 128x128 24-bit BMP into texture.h for the Demofruit rotozoom demo.

Usage:  python3 bmp2texture.py image.bmp [texture.h]

Produces a `texture[128][128]` RGB565 array plus the TEXTURE_W / TEXTURE_H /
TEXTURE_MASK defines the rotozoom demo expects. The rotozoom tiles this image
with a fast bitwise wrap, so the dimensions MUST be a power of two — 128x128.

Input requirements:
  - exactly 128 x 128 pixels
  - 24-bit uncompressed Windows BMP (no alpha, no RLE compression)
Bold, high-contrast content works best; rotozoom blurs fine detail.
"""

import sys
import os
import struct

EXPECT_W = 128
EXPECT_H = 128


def die(msg):
    print(f"error: {msg}")
    sys.exit(1)


if len(sys.argv) < 2:
    die("usage: python3 bmp2texture.py image.bmp [texture.h]")

src = sys.argv[1]
dst = sys.argv[2] if len(sys.argv) > 2 else "texture.h"

with open(src, "rb") as f:
    data = f.read()

# ── BMP file header (14 bytes) + DIB header ─────────────────────────────────
if data[0:2] != b"BM":
    die("not a BMP file (missing 'BM' signature)")

pixel_offset = struct.unpack("<I", data[10:14])[0]
dib_size     = struct.unpack("<I", data[14:18])[0]
width        = struct.unpack("<i", data[18:22])[0]
height       = struct.unpack("<i", data[22:26])[0]
bpp          = struct.unpack("<H", data[28:30])[0]
compression  = struct.unpack("<I", data[30:34])[0]

if bpp != 24:
    die(f"need 24-bit BMP, got {bpp}-bit (re-export as 24-bit uncompressed)")
if compression != 0:
    die("BMP is compressed; re-export as uncompressed (no RLE)")
if abs(width) != EXPECT_W or abs(height) != EXPECT_H:
    die(f"need {EXPECT_W}x{EXPECT_H}, got {abs(width)}x{abs(height)}")

# BMP rows are padded to 4-byte boundaries; 24bpp = 3 bytes/pixel
row_bytes = ((EXPECT_W * 3 + 3) & ~3)
top_down  = height < 0          # negative height = rows stored top-to-bottom

rows = []
for y in range(EXPECT_H):
    base = pixel_offset + y * row_bytes
    row = []
    for x in range(EXPECT_W):
        b = data[base + x * 3 + 0]
        g = data[base + x * 3 + 1]
        r = data[base + x * 3 + 2]
        rgb565 = ((r >> 3) << 11) | ((g >> 2) << 5) | (b >> 3)
        row.append(rgb565)
    rows.append(row)

# BMPs are bottom-up unless height is negative; flip to top-down for display
if not top_down:
    rows.reverse()

with open(dst, "w") as out:
    out.write(f"// {os.path.basename(dst)} — {EXPECT_W}x{EXPECT_H} RGB565 texture\n")
    out.write(f"// Generated from {os.path.basename(src)} by bmp2texture.py\n\n")
    out.write("#pragma once\n\n")
    out.write(f"#define TEXTURE_W  {EXPECT_W}\n")
    out.write(f"#define TEXTURE_H  {EXPECT_H}\n")
    out.write("#define TEXTURE_MASK  0x7F   // for fast power-of-2 wrap\n\n")
    out.write("static const uint16_t texture[TEXTURE_H][TEXTURE_W] = {\n")
    for y, row in enumerate(rows):
        out.write("  {" + ", ".join(f"0x{v:04X}" for v in row) + "}")
        out.write("," if y < EXPECT_H - 1 else "")
        out.write("\n")
    out.write("};\n")

print(f"{dst}: {EXPECT_W}x{EXPECT_H} written ({EXPECT_W*EXPECT_H*2} bytes of texture data)")
