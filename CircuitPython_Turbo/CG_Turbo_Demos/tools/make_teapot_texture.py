#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 John Park with Claude Opus 5.5 for Adafruit Industries
#
# SPDX-License-Identifier: MIT
"""The teapot's texture: CG_Turbo_Demos_Code/teapot_texture.bin, 512 x 512 little-endian
rgb565, rows top to bottom.

    python3 tools/make_teapot_texture.py [grid.png]

From the University of Utah's teapot page
(https://graphics.cs.utah.edu/teapot/): its UV test grid (A1 to H8, 1024 x
1024; reference/grid.png by default), scaled down, its grays stretched to
LOW..HIGH, and each part's region of the layout (tools/make_meshes.py)
tinted with the colors of the page's injective layout figure: body salmon,
handle green, knob yellow, lid peach, spout blue.
"""

import pathlib
import sys

import numpy as np
from PIL import Image

import make_meshes

ROOT = pathlib.Path(__file__).resolve().parent.parent
SIZE = make_meshes.TEXTURE
LOW, HIGH = 0.45, 1.0  # the darkest and lightest gray, times the part's color
COLORS = {  # RGB 0-1, from the figure's light checks
    "body": (0.85, 0.45, 0.45),
    "handle": (0.45, 0.85, 0.45),
    "knob": (0.95, 0.90, 0.45),
    "lid": (0.98, 0.78, 0.55),
    "spout": (0.45, 0.45, 0.85),
}


def regions():
    """Each texel's part, from the layout: names, as an array of strings."""
    layout = make_meshes.Layout(make_meshes.teapot_patches())
    knob = layout.splits[make_meshes.LID][1] * 0.25  # the knob's share of the lid disk's radius
    t, s = (np.mgrid[0:SIZE, 0:SIZE] + 0.5) / SIZE
    part = np.full((SIZE, SIZE), "lid", dtype=object)
    part[np.hypot(s - 0.25, t - 0.25) < knob] = "knob"
    part[(s >= 0.5) & (t < 0.25)] = "handle"
    part[(s >= 0.5) & (t >= 0.25) & (t < 0.5)] = "spout"
    part[t >= 0.5] = "body"
    return part


def main():
    source = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "reference" / "grid.png"
    image = Image.open(source).convert("L").resize((SIZE, SIZE), Image.LANCZOS)
    gray = np.asarray(image).astype(np.float64)
    lo, hi = np.percentile(gray, (1, 99))
    gray = np.clip(LOW + (gray - lo) * (HIGH - LOW) / (hi - lo), 0, 1)
    part = regions()
    color = np.zeros((SIZE, SIZE, 3))
    for name, rgb in COLORS.items():
        color[part == name] = rgb
    c = np.clip(gray[..., None] * color * 255 + 0.5, 0, 255).astype(np.uint32)
    texels = ((c[..., 0] >> 3) << 11) | ((c[..., 1] >> 2) << 5) | (c[..., 2] >> 3)
    out = ROOT / "CG_Turbo_Demos_Code" / "teapot_texture.bin"
    out.write_bytes(texels.astype("<u2").tobytes())
    print("wrote", out.relative_to(ROOT), out.stat().st_size, "bytes")


if __name__ == "__main__":
    main()
