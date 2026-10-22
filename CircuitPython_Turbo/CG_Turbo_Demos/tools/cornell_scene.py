#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 John Park with Claude Opus 5.5 for Adafruit Industries
#
# SPDX-License-Identifier: MIT
"""The Cornell box scene and the path tracer's parameter block layout.

    python3 tools/cornell_scene.py     # writes CG_Turbo_Demos_Code/cornell_scene.py

The box is the unit cube, seen through its open front (z = 0) from a pinhole
camera at z < 0: x = 0 is the red wall, x = 1 the green one, y = 0 the floor,
y = 1 the ceiling with the square light, z = 1 the back wall. Two spheres:
a diffuse one and a mirror.

Every float constant is shipped to the board as its float32 bit pattern, so
the board's FPU and the desktop's numpy float32 start from identical bits.
"""

from spdx import HEADER
import math
import pathlib
import struct

ROOT = pathlib.Path(__file__).resolve().parent.parent

SIZE = 240  # image width and height
DEPTH = 3  # surface interactions per path
EXPOSURE = 1.8

CAMERA = (0.5, 0.5, -1.35)
WHITE = (0.725, 0.71, 0.68)  # the classic Cornell box reflectances
RED = (0.63, 0.065, 0.05)
GREEN = (0.14, 0.45, 0.091)
LIGHT_MIN = 0.37  # the light: x and z from LIGHT_MIN to LIGHT_MIN + LIGHT_SIZE, at y = 1
LIGHT_SIZE = 0.26
EMISSION = (17.0, 12.0, 4.0)
DIFFUSE_SPHERE = ((0.70, 0.20, 0.38), 0.20, (0.75, 0.75, 0.75))  # center, radius, albedo
MIRROR_SPHERE = ((0.30, 0.25, 0.65), 0.25, 0.95)  # center, radius, reflectance
# The classic two boxes (button 3 swaps them in for the spheres), after the
# original's measurements in a 555-unit box, mirrored so red stays on the
# left: (center x, z on the floor), (width, height, depth), rotation about y.
BOXES = (
    ((0.665, 0.300), (0.300, 0.300, 0.300), -0.31),  # the short cube, front right
    ((0.335, 0.630), (0.270, 0.600, 0.270), 0.30),  # the tall box, rear left
)
BOX_FIELDS = ("CX", "CY", "CZ", "C", "S", "HX", "HY", "HZ", "NHX", "NHY", "NHZ")
EPSILON = 1e-4
FAR = 1e30

# The parameter block, one 32-bit word per slot. Integer slots come first:
# ldr offsets stop at 124 bytes; vldr reaches 1020.
INTS = [
    "ACCUM",  # address of this row's accumulation (3 floats per pixel)
    "OUT",  # address of this row's first output pixel (rgb565)
    "COUNT",  # pixels in the row
    "INDEX",  # image index of the row's first pixel (for the random seeds)
    "ROW",  # image row
    "PASS",  # pass number, from 0
    "SAMPLES",  # samples accumulated after this pass (pass + 1)
    "SEED_MUL",
    "PASS_MUL",
    "SEED_XOR",
    "ONE_BITS",  # 0x3F800000: random bits | ONE_BITS is a float in [1, 2)
    "COLUMN",  # working state
    "PIXEL",
    "SPECULAR",
    "BOUNCE",
    "MODE",  # 0: the two spheres, 1: the two boxes
    "HIT_FACE",  # working: box * 8 + axis * 2 + (1 for the + face)
]
FLOATS = [
    "ONE",
    "TWO",
    "ZERO",
    "EPSILON",
    "FAR",
    "INV_SIZE",
    "CAM_X",
    "CAM_Y",
    "CAM_Z",
    "LIGHT_MIN",
    "LIGHT_SIZE",
    "LIGHT_MAX",
    "LE_R",
    "LE_G",
    "LE_B",
    "LIGHT_K",  # light area / pi
    "WHITE_R",
    "WHITE_G",
    "WHITE_B",
    "RED_R",
    "RED_G",
    "RED_B",
    "GREEN_R",
    "GREEN_G",
    "GREEN_B",
    "D_X",  # diffuse sphere
    "D_Y",
    "D_Z",
    "D_R2",
    "D_INV_R",
    "D_ALB_R",
    "D_ALB_G",
    "D_ALB_B",
    "M_X",  # mirror sphere
    "M_Y",
    "M_Z",
    "M_R2",
    "M_INV_R",
    "M_ALB",
    "EXPOSURE",
    "K5",  # 31.999: [0, 1] to 5 bits
    "K6",  # 63.999: [0, 1] to 6 bits
    "SCALE",  # working: exposure / samples
] + ["B%d_%s" % (b, f) for b in range(2) for f in BOX_FIELDS]
SAVE = 16  # s16-s31 belong to the caller: saved here
INT_BASE = 0
FLOAT_BASE = 32
SAVE_BASE = FLOAT_BASE + len(FLOATS)
WORDS = SAVE_BASE + SAVE

WALL_NAMES = ("RED_R", "RED_G", "RED_B", "GREEN_R", "GREEN_G", "GREEN_B")

SEED_MUL = 0x9E3779B1
PASS_MUL = 0x85EBCA6B
SEED_XOR = 0x2545F491


def slot(name):
    if name in INTS:
        return INT_BASE + INTS.index(name)
    return FLOAT_BASE + FLOATS.index(name)


def f32_bits(value):
    return struct.unpack("<I", struct.pack("<f", value))[0]


def float_values(white_walls=False):
    """The float constants; white_walls paints the red and green walls white."""
    red, green = (WHITE, WHITE) if white_walls else (RED, GREEN)
    (dx, dy, dz), dr, dalb = DIFFUSE_SPHERE
    (mx, my, mz), mr, malb = MIRROR_SPHERE
    return {
        "ONE": 1.0,
        "TWO": 2.0,
        "ZERO": 0.0,
        "EPSILON": EPSILON,
        "FAR": FAR,
        "INV_SIZE": 1.0 / SIZE,
        "CAM_X": CAMERA[0],
        "CAM_Y": CAMERA[1],
        "CAM_Z": CAMERA[2],
        "LIGHT_MIN": LIGHT_MIN,
        "LIGHT_SIZE": LIGHT_SIZE,
        "LIGHT_MAX": LIGHT_MIN + LIGHT_SIZE,
        "LE_R": EMISSION[0],
        "LE_G": EMISSION[1],
        "LE_B": EMISSION[2],
        "LIGHT_K": LIGHT_SIZE * LIGHT_SIZE / math.pi,
        "WHITE_R": WHITE[0],
        "WHITE_G": WHITE[1],
        "WHITE_B": WHITE[2],
        "RED_R": red[0],
        "RED_G": red[1],
        "RED_B": red[2],
        "GREEN_R": green[0],
        "GREEN_G": green[1],
        "GREEN_B": green[2],
        "D_X": dx,
        "D_Y": dy,
        "D_Z": dz,
        "D_R2": dr * dr,
        "D_INV_R": 1.0 / dr,
        "D_ALB_R": dalb[0],
        "D_ALB_G": dalb[1],
        "D_ALB_B": dalb[2],
        "M_X": mx,
        "M_Y": my,
        "M_Z": mz,
        "M_R2": mr * mr,
        "M_INV_R": 1.0 / mr,
        "M_ALB": malb,
        "EXPOSURE": EXPOSURE,
        "K5": 31.999,
        "K6": 63.999,
        "SCALE": 0.0,
        **box_values(),
    }


def box_values():
    values = {}
    for b, ((cx, cz), (w, h, d), angle) in enumerate(BOXES):
        hx, hy, hz = w / 2, h / 2, d / 2
        for field, value in zip(
            BOX_FIELDS, (cx, hy, cz, math.cos(angle), math.sin(angle), hx, hy, hz, -hx, -hy, -hz)
        ):
            values["B%d_%s" % (b, field)] = value
    return values


def block_words():
    """The block's initial contents as u32 words."""
    words = [0] * WORDS
    for name, value in float_values().items():
        words[slot(name)] = f32_bits(value)
    words[slot("SEED_MUL")] = SEED_MUL
    words[slot("PASS_MUL")] = PASS_MUL
    words[slot("SEED_XOR")] = SEED_XOR
    words[slot("ONE_BITS")] = 0x3F800000
    words[slot("COUNT")] = SIZE
    return words


def main():
    lines = [
        '"""Generated by tools/cornell_scene.py: edit that."""',
        "",
        "SIZE = %d" % SIZE,
        "WORDS = %d" % WORDS,
    ]
    for name in INTS:
        lines.append("%s = %d" % (name, slot(name)))
    lines.append("SCALE = %d" % slot("SCALE"))
    lines.append("EXPOSURE = %d" % slot("EXPOSURE"))
    lines.append("MODE = %d" % slot("MODE"))
    lines.append("# the side walls' color slots, and their words for each look")
    lines.append("WALL_SLOTS = (%s)" % ", ".join(str(slot(n)) for n in WALL_NAMES))
    for name, white in (("COLORED_WALLS", False), ("WHITE_WALLS", True)):
        values = float_values(white)
        lines.append("%s = (%s)" % (name, ", ".join("0x%08X" % f32_bits(values[n]) for n in WALL_NAMES)))
    lines.append("# the block's initial words (float constants as float32 bit patterns)")
    lines.append("BLOCK = (")
    words = block_words()
    for i in range(0, len(words), 6):
        lines.append("    " + " ".join("0x%08X," % w for w in words[i : i + 6]))
    lines.append(")")
    out = ROOT / "CG_Turbo_Demos_Code" / "cornell_scene.py"
    out.write_text(HEADER + "\n".join(lines) + "\n")
    print("wrote", out.relative_to(ROOT))


if __name__ == "__main__":
    main()
