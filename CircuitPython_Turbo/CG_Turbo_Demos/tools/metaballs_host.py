#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 John Park with Claude Opus 5.5 for Adafruit Industries
#
# SPDX-License-Identifier: MIT
"""Render 2D metaballs frames on the desktop with the viper reference.

    python3 tools/metaballs_host.py --time 0 --out build/metaballs.png
    python3 tools/metaballs_host.py --dump frame.bin   # raw rgb565, to compare with the board

Uses the same turbo_source/metaballs.py, CG_Turbo_Demos_Code/metafield.py and CG_Turbo_Demos_Code/blobs.py (the
animation) as the board.
"""

import argparse
import pathlib
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT / "tools" / "host"), str(ROOT / "turbo_source"), str(ROOT / "CG_Turbo_Demos_Code"), str(ROOT / "tools")]

import blobs  # noqa: E402
import metaballs  # noqa: E402
import metafield  # noqa: E402
from voxel_host import to_image  # noqa: E402

WIDTH, HEIGHT = 320, 200


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--time", type=float, default=0.0, help="animation time, seconds")
    parser.add_argument("--out", type=pathlib.Path, default=ROOT / "build" / "metaballs.png")
    parser.add_argument("--dump", type=pathlib.Path)
    parser.add_argument("--balls", type=int, default=blobs.START)
    parser.add_argument("--hue", type=int, default=0, help="presses of button 1")
    parser.add_argument("--no-glow", action="store_true", help="a double click of button 1")
    options = parser.parse_args()
    space = metafield.Metaballs(
        WIDTH, HEIGHT, str(ROOT / "CG_Turbo_Demos_Code" / "metaballs.bin"), buffer_view=lambda b: memoryview(b).cast("H")
    )
    space.kernel = metaballs.render  # the asm only runs on the board
    for _ in range(options.hue):
        space.next_hue()
    space.show_glow(not options.no_glow)
    space.set_balls(blobs.positions(options.time, WIDTH, HEIGHT, options.balls))
    back = bytearray(WIDTH * HEIGHT * 2)
    start = time.monotonic()
    space.render(memoryview(back).cast("H"))
    print("rendered in %.2f s on the host" % (time.monotonic() - start))
    options.out.parent.mkdir(exist_ok=True)
    to_image(back).save(options.out)
    print("wrote", options.out)
    if options.dump:
        options.dump.write_bytes(back)


if __name__ == "__main__":
    main()
