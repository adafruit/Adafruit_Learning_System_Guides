#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 John Park with Claude Opus 5.5 for Adafruit Industries
#
# SPDX-License-Identifier: MIT
"""Measure how much the VoxelSpace fly-over flickers, on the desktop.

    python3 tools/voxel_flicker.py --frames 120 --start 300

Renders consecutive frames of CG_Turbo_Demos_Code/flight.py's path with the viper reference
and reports the mean second temporal difference of luminance,
|f(t+1) - 2 f(t) + f(t-1)|: steady motion scores low, values that jump back
and forth (aliasing) score high. Also saves the last frame to look at.
"""

import argparse
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT / "tools" / "host"), str(ROOT / "turbo_source"), str(ROOT / "CG_Turbo_Demos_Code"), str(ROOT / "tools")]

import numpy as np  # noqa: E402
from PIL import Image  # noqa: E402

import flight  # noqa: E402
import voxel  # noqa: E402
import voxelspace  # noqa: E402
from voxel_host import HEIGHT, WIDTH, to_image  # noqa: E402


def luminance(back):
    p = np.frombuffer(back, dtype="<u2").reshape(HEIGHT, WIDTH).astype(np.int32)
    return ((p >> 11) << 3) * 0.3 + (((p >> 5) & 63) << 2) * 0.59 + ((p & 31) << 3) * 0.11


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--frames", type=int, default=120)
    parser.add_argument("--start", type=int, default=300, help="flight frames to skip first")
    parser.add_argument("--assets", type=pathlib.Path, default=ROOT / "CG_Turbo_Demos_Code")
    parser.add_argument("--strip", type=pathlib.Path, default=ROOT / "build" / "flicker_last.png")
    parser.add_argument("--growth", type=float, default=0.016)
    parser.add_argument("--mips", type=int, nargs=2, help="distances where levels 1, 2 start")
    options = parser.parse_args()
    space = voxelspace.VoxelSpace(
        WIDTH,
        HEIGHT,
        str(options.assets / "terrain16.bin"),
        str(options.assets / "palette.bin"),
        512,
        growth=options.growth,
        buffer_view=lambda b: memoryview(b).cast("H"),
        **({"mips": tuple(options.mips)} if options.mips else {}),
    )
    space.kernel = voxel.render
    path = flight.Flight(space)
    for _ in range(options.start):
        path.step()
    frames = []
    back = bytearray(WIDTH * HEIGHT * 2)
    for _ in range(options.frames):
        path.step()
        space.render(memoryview(back).cast("H"))
        frames.append(luminance(back))
    f = np.stack(frames)
    second = np.abs(f[2:] - 2 * f[1:-1] + f[:-2])
    rows = second.mean(axis=(0, 2))
    print("flicker %.2f (mean |2nd temporal difference|, 0-255 luminance)" % second.mean())
    for name, band in (("near (rows 150-199)", rows[150:]), ("middle (100-149)", rows[100:150]), ("far (60-99)", rows[60:100])):
        print("  %-20s %.2f" % (name, band.mean()))
    options.strip.parent.mkdir(exist_ok=True)
    to_image(back).save(options.strip)


if __name__ == "__main__":
    main()
