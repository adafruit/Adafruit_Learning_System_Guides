#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 John Park with Claude Opus 5.5 for Adafruit Industries
#
# SPDX-License-Identifier: MIT
"""Render VoxelSpace frames on the desktop with the viper reference kernel.

    python3 tools/voxel_host.py --x 256 --y 256 --angle 0 --out view.png
    python3 tools/voxel_host.py --dump frame.bin   # raw rgb565, to compare with the board

Uses the same turbo_source/voxel.py and CG_Turbo_Demos_Code/voxelspace.py as the board.
"""

import argparse
import pathlib
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT / "tools" / "host"), str(ROOT / "turbo_source"), str(ROOT / "CG_Turbo_Demos_Code")]

import numpy as np  # noqa: E402
from PIL import Image  # noqa: E402

import voxel  # noqa: E402
import voxelspace  # noqa: E402

WIDTH, HEIGHT = 320, 200


def to_image(back, scale=2):
    p = np.frombuffer(back, dtype="<u2").reshape(HEIGHT, WIDTH).astype(np.uint32)
    rgb = np.stack([(p >> 11) << 3, ((p >> 5) & 63) << 2, (p & 31) << 3], axis=-1).astype(np.uint8)
    image = Image.fromarray(rgb)
    return image.resize((WIDTH * scale, HEIGHT * scale), Image.NEAREST)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--terrain", type=pathlib.Path, default=ROOT / "CG_Turbo_Demos_Code" / "terrain16.bin")
    parser.add_argument("--palette", type=pathlib.Path, default=ROOT / "CG_Turbo_Demos_Code" / "palette.bin")
    parser.add_argument("--size", type=int, default=512)
    parser.add_argument("--x", type=float, default=256)
    parser.add_argument("--y", type=float, default=300)
    parser.add_argument("--above", type=float, default=70, help="camera height above the ground")
    parser.add_argument("--angle", type=float, default=0.0)
    parser.add_argument("--horizon", type=int, default=60)
    parser.add_argument("--out", type=pathlib.Path, default=ROOT / "build" / "voxel_host.png")
    parser.add_argument("--dump", type=pathlib.Path)
    parser.add_argument("--mode", choices=voxelspace.VoxelSpace.MODES, default="color")
    parser.add_argument("--height-scale", type=int, default=0, help="presses of button 2: 0 full ... 4 flat")
    parser.add_argument("--no-fog", action="store_true")
    options = parser.parse_args()

    space = voxelspace.VoxelSpace(
        WIDTH,
        HEIGHT,
        str(options.terrain),
        str(options.palette),
        options.size,
        shade_path=str(options.terrain.parent / "shade.bin"),
        buffer_view=lambda b: memoryview(b).cast("H"),
    )
    space.show(options.mode)
    for _ in range(options.height_scale):
        space.next_height_scale()
    space.show_fog(not options.no_fog)
    space.kernel = voxel.render  # the asm kernels only run on the board
    h = space.height_at(options.x, options.y) + options.above
    space.view(options.x, options.y, h, options.angle, options.horizon)
    back = bytearray(WIDTH * HEIGHT * 2)
    start = time.monotonic()
    space.render(memoryview(back).cast("H"))
    print("%d rows, rendered in %.2f s on the host" % (space.rows, time.monotonic() - start))
    options.out.parent.mkdir(exist_ok=True)
    to_image(back).save(options.out)
    print("wrote", options.out)
    if options.dump:
        options.dump.write_bytes(back)


if __name__ == "__main__":
    main()
