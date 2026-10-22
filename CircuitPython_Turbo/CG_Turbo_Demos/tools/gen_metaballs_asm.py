#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 John Park with Claude Opus 5.5 for Adafruit Industries
#
# SPDX-License-Identifier: MIT
"""Write turbo_source/metaballs_asm.py: a whole 2D metaballs frame as one asm_thumb function.

    python3 tools/gen_metaballs_asm.py

frame_asm(args_address) must produce exactly the pixels of
metaballs.render(). Its row sums are interleaved per pixel (field, gradient
x, gradient y: 12 bytes), unlike the reference's three arrays, so one pointer
reaches all three; they are cleared as each row is shaded. Slot offsets come
from turbo_source/metaballs.py's F_* constants.
"""

from spdx import HEADER
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parent.parent

source = (ROOT / "turbo_source" / "metaballs.py").read_text()
consts = {name: int(value) for name, value in re.findall(r"^(\w+) = const\((\d+)\)", source, re.M)}


def at(name):
    offset = 4 * consts[name]
    if offset > 124:
        raise SystemExit("%s is past the 124-byte ldr/str offset limit" % name)
    return "[r7, %d]" % offset


BODY = '''
    ldr(r7, [r3, 0])
    push({r7})
    asr(r7, r7, 1)
    mov(r3, r8)  # r8-r11 belong to the caller
    mov(r4, r9)
    mov(r5, r10)
    mov(r6, r11)
    push({r3, r4, r5, r6})

    # clear the row sums (the shading below keeps them clear)
    ldr(r1, F_ROW)
    ldr(r2, F_ROW_END)
    mov(r0, 0)
    label(clear)
    str(r0, [r1, 0])
    add(r1, 4)
    cmp(r1, r2)
    blt(clear)

    label(row)
    ldr(r6, F_BALLS)
    str(r6, F_BALL)
    ldr(r3, F_BALLS_END)
    cmp(r6, r3)
    bge_w(shade)

    label(ball)
    ldr(r6, F_BALL)
    # dy = y16 - ball y; h2 = r2 - dy * dy
    ldr(r3, [r6, B_Y4])
    ldr(r4, F_Y16)
    sub(r4, r4, r3)
    mov(r10, r4)
    mov(r3, r4)
    mul(r3, r4)
    ldr(r5, [r6, B_R24])
    sub(r5, r5, r3)
    ble_w(ball_next)
    mov(r8, r5)
    ldr(r3, [r6, B_INV4])
    mov(r9, r3)
    # columns x0..x1 of the ball's bounding span, clipped to the row
    ldr(r0, [r6, B_X4])
    ldr(r1, [r6, B_R4])
    sub(r2, r0, r1)
    asr(r2, r2, 4)
    bpl(x0_ok)
    mov(r2, 0)
    label(x0_ok)
    add(r3, r0, r1)
    asr(r3, r3, 4)
    ldr(r5, A_WIDTH_AT)
    sub(r5, r5, 1)
    cmp(r3, r5)
    ble(x1_ok)
    mov(r3, r5)
    label(x1_ok)
    sub(r3, r3, r2)
    add(r3, r3, 1)
    ble_w(ball_next)
    # dx = (x0 << 4) + 8 - x; pointer = row + x0 * 12
    lsl(r4, r2, 4)
    add(r4, 8)
    sub(r0, r4, r0)
    lsl(r4, r2, 2)
    lsl(r5, r2, 3)
    add(r4, r4, r5)
    ldr(r1, F_ROW)
    add(r1, r1, r4)
    mov(r2, r3)

    # r0 dx, r1 the column's sums, r2 columns left; r8 h2, r9 inv, r10 dy
    label(column)
    mov(r3, r0)
    mul(r3, r0)
    mov(r4, r8)
    sub(r4, r4, r3)
    ble(column_next)
    mov(r3, r9)
    mul(r4, r3)
    asr(r4, r4, 16)  # qn: 1 - d^2/R^2, 12 fractional bits
    mov(r3, r4)
    mul(r3, r4)
    asr(r3, r3, 12)
    ldr(r5, [r1, 0])
    add(r5, r5, r3)
    str(r5, [r1, 0])
    mov(r3, r4)
    mul(r3, r0)
    asr(r3, r3, 4)
    mov(r5, r9)
    mul(r3, r5)
    asr(r3, r3, 16)
    ldr(r5, [r1, 4])
    add(r5, r5, r3)
    str(r5, [r1, 4])
    mov(r3, r4)
    mov(r5, r10)
    mul(r3, r5)
    asr(r3, r3, 4)
    mov(r5, r9)
    mul(r3, r5)
    asr(r3, r3, 16)
    ldr(r5, [r1, 8])
    add(r5, r5, r3)
    str(r5, [r1, 8])
    label(column_next)
    add(r0, 16)
    add(r1, 12)
    sub(r2, r2, 1)
    bgt(column)

    label(ball_next)
    ldr(r6, F_BALL)
    add(r6, 20)
    str(r6, F_BALL)
    ldr(r3, F_BALLS_END)
    cmp(r6, r3)
    blt_w(ball)

    # shade the row: r0 the pixel, r1 the column's sums, r2 columns left;
    # r8 threshold, r9 tables, r10 slope shift, r11 glow shift
    label(shade)
    ldr(r3, A_THRESHOLD_AT)
    mov(r8, r3)
    ldr(r3, F_TABLES)
    mov(r9, r3)
    ldr(r3, A_SLOPE_SHIFT_AT)
    mov(r10, r3)
    ldr(r3, A_GLOW_SHIFT_AT)
    mov(r11, r3)
    ldr(r0, F_OUT)
    ldr(r1, F_ROW)
    ldr(r2, A_WIDTH_AT)
    label(pixel)
    ldr(r3, [r1, 0])
    cmp(r3, 0)
    bne(lit)
    # no field here (most of the screen): the glow palette's first color
    mov(r4, r9)
    ldrh(r4, [r4, 0])
    strh(r4, [r0, 0])
    b(pixel_next)
    label(lit)
    ldr(r4, [r1, 4])
    ldr(r5, [r1, 8])
    mov(r6, 0)
    str(r6, [r1, 0])
    str(r6, [r1, 4])
    str(r6, [r1, 8])
    mov(r6, r8)
    cmp(r3, r6)
    blt_w(outside)
    # inside: slope = gradient * scale[(f - threshold) >> 3] >> slope shift
    sub(r3, r3, r6)
    asr(r3, r3, 3)
    cmp(r3, 255)
    ble(t_ok)
    mov(r3, 255)
    label(t_ok)
    lsl(r3, r3, 1)
    mov(r6, r9)
    add(r3, r3, r6)
    movw(r6, SCALES_BYTES)
    add(r3, r3, r6)
    ldrh(r3, [r3, 0])
    mov(r6, r10)
    mul(r4, r3)
    asr(r4, r6)
    add(r4, 32)
    bpl(gx_low_ok)
    mov(r4, 0)
    label(gx_low_ok)
    cmp(r4, 63)
    ble(gx_ok)
    mov(r4, 63)
    label(gx_ok)
    mul(r5, r3)
    asr(r5, r6)
    add(r5, 32)
    bpl(gy_low_ok)
    mov(r5, 0)
    label(gy_low_ok)
    cmp(r5, 63)
    ble(gy_ok)
    mov(r5, 63)
    label(gy_ok)
    lsl(r5, r5, 7)
    lsl(r4, r4, 1)
    add(r5, r5, r4)
    mov(r6, r9)
    add(r5, r5, r6)
    movw(r6, SHADES_BYTES)
    add(r5, r5, r6)
    ldrh(r5, [r5, 0])
    strh(r5, [r0, 0])
    b(pixel_next)
    label(outside)
    mov(r6, r11)
    asr(r3, r6)
    cmp(r3, 255)
    ble(g_ok)
    mov(r3, 255)
    label(g_ok)
    lsl(r3, r3, 1)
    mov(r6, r9)
    add(r3, r3, r6)
    ldrh(r3, [r3, 0])
    strh(r3, [r0, 0])
    label(pixel_next)
    add(r0, 2)
    add(r1, 12)
    sub(r2, r2, 1)
    bgt_w(pixel)
    str(r0, F_OUT)

    # next row
    ldr(r3, F_Y16)
    add(r3, 16)
    str(r3, F_Y16)
    ldr(r3, F_Y)
    add(r3, 1)
    str(r3, F_Y)
    ldr(r4, A_HEIGHT_AT)
    cmp(r3, r4)
    blt_w(row)

    pop({r3, r4, r5, r6})
    mov(r8, r3)
    mov(r9, r4)
    mov(r10, r5)
    mov(r11, r6)
    pop({r0})
'''

HEAD = '''"""Generated by tools/gen_metaballs_asm.py: edit that.

frame_asm(args_address): one whole 2D metaballs frame, bit-identical to
metaballs.render(). Relabelled as viper by tools/asm_to_viper.py, so the
argument object is at [r3].
"""

import micropython


@micropython.asm_thumb
def frame_asm(r0, r1, r2, r3):'''


def main():
    body = BODY
    names = {
        "A_WIDTH_AT": at("A_WIDTH"),
        "A_HEIGHT_AT": at("A_HEIGHT"),
        "A_THRESHOLD_AT": at("A_THRESHOLD"),
        "A_SLOPE_SHIFT_AT": at("A_SLOPE_SHIFT"),
        "A_GLOW_SHIFT_AT": at("A_GLOW_SHIFT"),
        "B_X4": str(4 * consts["B_X"]),
        "B_Y4": str(4 * consts["B_Y"]),
        "B_R4": str(4 * consts["B_R"]),
        "B_R24": str(4 * consts["B_R2"]),
        "B_INV4": str(4 * consts["B_INV"]),
        "SCALES_BYTES": str(2 * consts["SCALES_AT"]),
        "SHADES_BYTES": str(2 * consts["GLOW"]),
    }
    names.update({name: at(name) for name in consts if name.startswith("F_")})
    for name in sorted(names, key=len, reverse=True):
        body = re.sub(r"\b%s\b" % name, names[name], body)
    if 4 * consts["BALL"] != 20:
        raise SystemExit("ball_next assumes 5 ints per ball")
    out = ROOT / "turbo_source" / "metaballs_asm.py"
    out.write_text(HEADER + HEAD + body)
    print("wrote", out.relative_to(ROOT))


if __name__ == "__main__":
    main()
