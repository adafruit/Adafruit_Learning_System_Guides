// SPDX-FileCopyrightText: Copyright (c) 2026 Tim Cocks for Adafruit Industries
// SPDX-License-Identifier: GPL-3.0-or-later
// void tf_ctx_switch(tf_ctx *save, const tf_ctx *load)
// Saves the callee-saved integer registers (ra, sp, s0-s11) of the current
// context into *save and continues the context in *load. The module is built
// for rv32imac (no FPU code), so the caller's fs0-fs11 are left untouched
// across the switch and need no saving.

    .text
    .globl tf_ctx_switch
    .type tf_ctx_switch, @function
    .align 2
tf_ctx_switch:
    sw ra,   0(a0)
    sw sp,   4(a0)
    sw s0,   8(a0)
    sw s1,  12(a0)
    sw s2,  16(a0)
    sw s3,  20(a0)
    sw s4,  24(a0)
    sw s5,  28(a0)
    sw s6,  32(a0)
    sw s7,  36(a0)
    sw s8,  40(a0)
    sw s9,  44(a0)
    sw s10, 48(a0)
    sw s11, 52(a0)

    lw ra,   0(a1)
    lw sp,   4(a1)
    lw s0,   8(a1)
    lw s1,  12(a1)
    lw s2,  16(a1)
    lw s3,  20(a1)
    lw s4,  24(a1)
    lw s5,  28(a1)
    lw s6,  32(a1)
    lw s7,  36(a1)
    lw s8,  40(a1)
    lw s9,  44(a1)
    lw s10, 48(a1)
    lw s11, 52(a1)
    ret
    .size tf_ctx_switch, .-tf_ctx_switch
