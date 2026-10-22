#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 John Park with Claude Opus 5.5 for Adafruit Industries
#
# SPDX-License-Identifier: MIT
"""The boot menu's thumbnails: CG_Turbo_Demos_Code/menu_*.bmp, 80 x 50, 24-bit.

    python3 tools/make_menu_thumbs.py

Each is a frame from that demo's desktop reference renderer, so it shows
what the demo draws. Needs the demos' assets (and CG_Turbo_Demos_Code/bunny.bin is not
used: the 3D thumbnail shows the teapot).
"""

import pathlib
import subprocess
import sys

from PIL import Image

ROOT = pathlib.Path(__file__).resolve().parent.parent
BUILD = ROOT / "build"
SIZE = (80, 50)


def crop_to(image, aspect):
    """Center-crop image to width / height = aspect."""
    w, h = image.size
    if w / h > aspect:
        nw = round(h * aspect)
        return image.crop(((w - nw) // 2, 0, (w - nw) // 2 + nw, h))
    nh = round(w / aspect)
    return image.crop((0, (h - nh) // 2, w, (h - nh) // 2 + nh))


def fit(image):
    """The whole image, scaled to the thumbnail's height, centered on black."""
    w, h = image.size
    scaled = image.resize((round(w * SIZE[1] / h), SIZE[1]), Image.LANCZOS)
    thumb = Image.new("RGB", SIZE)
    thumb.paste(scaled, ((SIZE[0] - scaled.width) // 2, 0))
    return thumb


def render(name, command, out, whole=False):
    subprocess.run([sys.executable] + command + ["--out", str(out)], check=True, capture_output=True, cwd=ROOT)
    image = Image.open(out).convert("RGB")
    if whole:
        thumb = fit(image)
    else:
        thumb = crop_to(image, SIZE[0] / SIZE[1]).resize(SIZE, Image.LANCZOS)
    path = ROOT / "CG_Turbo_Demos_Code" / ("menu_%s.bmp" % name)
    thumb.save(path)
    print("wrote", path.relative_to(ROOT))


def main():
    BUILD.mkdir(exist_ok=True)
    render("voxel", ["tools/voxel_host.py", "--x", "200", "--y", "330", "--angle", "0.6", "--above", "60"], BUILD / "thumb_voxel.png")
    render("cornell", ["tools/cornell_ref.py", "--passes", "128", "--boxes"], BUILD / "thumb_cornell.png", whole=True)
    render("metaballs", ["tools/metaballs_host.py", "--time", "3"], BUILD / "thumb_metaballs.png")
    render("meshes", ["tools/mesh_ref.py", "--mesh", "teapot", "--mode", "phong", "--angle", "2.2"], BUILD / "thumb_meshes.png")


if __name__ == "__main__":
    main()
