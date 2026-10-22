# SPDX-FileCopyrightText: 2026 John Park with Claude Opus 5.5 for Adafruit Industries
#
# SPDX-License-Identifier: MIT
"""Does single-precision FPU code work in relabelled asm_thumb on the RP2350?"""

import micropython


@micropython.asm_thumb
def sqrt_milli(r0, r1, r2, r3):
    # sqrt_milli(n) -> int(sqrt(n) * 1000), n a small int, through the FPU.
    ldr(r0, [r3, 0])
    asr(r0, r0, 1)
    vmov(s0, r0)
    vcvt_f32_s32(s0, s0)
    vsqrt(s0, s0)
    movw(r1, 1000)
    vmov(s1, r1)
    vcvt_f32_s32(s1, s1)
    vmul(s0, s0, s1)
    vcvt_s32_f32(s0, s0)
    vmov(r0, s0)
    # return it as a small int object
    lsl(r0, r0, 1)
    add(r0, r0, 1)


@micropython.asm_thumb
def fdiv_loop(r0, r1, r2, r3):
    # fdiv_loop(count) -> count: count dependent vdiv+vsqrt pairs, for timing.
    ldr(r0, [r3, 0])
    push({r0})
    asr(r0, r0, 1)
    movw(r1, 3)
    vmov(s0, r1)
    vcvt_f32_s32(s0, s0)
    vmov(r2, s0)
    vmov(s1, r2)
    label(loop)
    vdiv(s0, s1, s0)
    vsqrt(s0, s0)
    sub(r0, r0, 1)
    bgt(loop)
    pop({r0})
