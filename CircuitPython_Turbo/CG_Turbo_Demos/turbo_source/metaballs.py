# SPDX-FileCopyrightText: 2026 John Park with Claude Opus 5.5 for Adafruit Industries
#
# SPDX-License-Identifier: MIT
"""2D metaballs kernels.

render() is the readable viper reference: indexed access only, so the same
source also runs on a desktop under tools/host/micropython.py.
render_fast() runs the whole frame in metaballs_asm.frame_asm() and must
produce identical pixels.

Each ball adds Wyvill's falloff w = (1 - d^2/R^2)^2 (zero beyond R) to the
field, and its gradient to two gradient sums, over its bounding span of each
row. Inside the threshold, the slope of z = sqrt(field - threshold)
(the gradient times a table scale) indexes a 64 x 64 shading table (a lit
surface with that slope); outside, the field indexes a glow palette.
All integer math. Positions are in 1/16 pixels.
"""

import micropython
from micropython import const

from metaballs_asm import frame_asm

A_WIDTH = const(0)
A_HEIGHT = const(1)
A_BALLS = const(2)  # number of balls
A_THRESHOLD = const(3)  # field value where the blobs' surface is
A_GLOW_SHIFT = const(4)  # field >> this indexes the glow palette
A_SLOPE_SHIFT = const(5)  # (gradient * scale) >> this indexes the shading table
A_BALLS_AT = const(6)  # BALL ints per ball
A_ROW_AT = const(7)  # 3 * width ints: field, gradient x, gradient y

# Slots 8-31: what frame_asm() reads (ldr offsets stop at 124 bytes), filled
# by render_fast(); tools/gen_metaballs_asm.py writes the asm from these names.
F_OUT = const(8)  # address of the next output pixel
F_TABLES = const(9)
F_ROW = const(10)  # address of the row sums (interleaved per pixel in the asm)
F_ROW_END = const(11)
F_BALLS = const(12)  # address of the first ball
F_BALLS_END = const(13)
F_BALL = const(14)  # working: the ball being added
F_Y = const(15)  # working: the row
F_Y16 = const(16)  # working: the row's center, 1/16 pixels
HEADER = const(32)

BALL = const(5)
B_X = const(0)  # center, 1/16 pixels
B_Y = const(1)
B_R = const(2)  # radius, 1/16 pixels
B_R2 = const(3)  # radius squared
B_INV = const(4)  # (1 << 28) // radius squared

GLOW = const(256)  # the tables: GLOW glow colors, SHADES x SHADES shades, SCALES slope scales
SHADES = const(64)
SCALES = const(256)
SCALES_AT = const(4352)  # GLOW + SHADES * SHADES


@micropython.viper
def render(back: ptr16, tables: ptr16, args: ptr32):
    w = args[A_WIDTH]
    h = args[A_HEIGHT]
    balls = args[A_BALLS]
    threshold = args[A_THRESHOLD]
    glow_shift = args[A_GLOW_SHIFT]
    slope_shift = args[A_SLOPE_SHIFT]
    balls_at = args[A_BALLS_AT]
    field = args[A_ROW_AT]
    grad_x = field + w
    grad_y = grad_x + w
    o = 0
    y = 0
    while y < h:
        i = 0
        while i < w:
            args[field + i] = 0
            args[grad_x + i] = 0
            args[grad_y + i] = 0
            i += 1
        y16 = (y << 4) + 8  # the pixel's center
        b = 0
        while b < balls:
            k = balls_at + BALL * b
            cx = args[k + B_X]
            r = args[k + B_R]
            dy = y16 - args[k + B_Y]
            h2 = args[k + B_R2] - dy * dy
            if h2 > 0:
                inv = args[k + B_INV]
                x0 = (cx - r) >> 4
                x1 = (cx + r) >> 4
                if x0 < 0:
                    x0 = 0
                if x1 > w - 1:
                    x1 = w - 1
                x = x0
                while x <= x1:
                    dx = (x << 4) + 8 - cx
                    q = h2 - dx * dx
                    if q > 0:
                        qn = (q * inv) >> 16  # 1 - d^2/R^2, 12 fractional bits
                        args[field + x] += (qn * qn) >> 12
                        args[grad_x + x] += (((qn * dx) >> 4) * inv) >> 16
                        args[grad_y + x] += (((qn * dy) >> 4) * inv) >> 16
                    x += 1
            b += 1
        x = 0
        while x < w:
            f = args[field + x]
            if f >= threshold:
                t = (f - threshold) >> 3
                if t > 255:
                    t = 255
                scale = tables[SCALES_AT + t]
                gx = ((args[grad_x + x] * scale) >> slope_shift) + 32
                gy = ((args[grad_y + x] * scale) >> slope_shift) + 32
                if gx < 0:
                    gx = 0
                if gx > 63:
                    gx = 63
                if gy < 0:
                    gy = 0
                if gy > 63:
                    gy = 63
                back[o] = tables[GLOW + (gy << 6) + gx]
            else:
                g = f >> glow_shift
                if g > 255:
                    g = 255
                back[o] = tables[g]
            o += 1
            x += 1
        y += 1


@micropython.viper
def render_fast(back: ptr16, tables: ptr16, args: ptr32):
    """render() as one frame_asm() call: same pixels."""
    base = int(args)
    w = args[A_WIDTH]
    args[F_OUT] = int(back)
    args[F_TABLES] = int(tables)
    args[F_ROW] = base + 4 * args[A_ROW_AT]
    args[F_ROW_END] = base + 4 * args[A_ROW_AT] + 12 * w
    args[F_BALLS] = base + 4 * args[A_BALLS_AT]
    args[F_BALLS_END] = base + 4 * args[A_BALLS_AT] + 4 * BALL * args[A_BALLS]
    args[F_Y] = 0
    args[F_Y16] = 8
    frame_asm(base)
