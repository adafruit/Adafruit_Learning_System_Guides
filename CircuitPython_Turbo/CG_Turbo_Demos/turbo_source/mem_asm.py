# SPDX-FileCopyrightText: 2026 John Park with Claude Opus 5.5 for Adafruit Industries
#
# SPDX-License-Identifier: MIT
"""Memory copies in asm_thumb: relabelled as viper by tools/asm_to_viper.py,
so the argument object is at [r3]."""

import micropython


@micropython.asm_thumb
def copy_rows_asm(r0, r1, r2, r3):
    """copy_rows_asm(block): block is the address of 5 int32 words: dst, src,
    rows, words per row (a multiple of 4), dst's row stride in bytes. Copies
    rows packed at src to rows stride apart at dst: a narrow back buffer into
    the screen."""
    ldr(r7, [r3, 0])
    push({r7})
    asr(r7, r7, 1)
    ldr(r0, [r7, 0])  # dst row
    ldr(r1, [r7, 4])  # src
    ldr(r2, [r7, 8])  # rows
    ldr(r3, [r7, 12])  # words per row
    ldr(r4, [r7, 16])  # stride
    label(row)
    mov(r5, r3)
    mov(r6, r0)
    label(words)
    ldr(r7, [r1, 0])
    str(r7, [r6, 0])
    ldr(r7, [r1, 4])
    str(r7, [r6, 4])
    ldr(r7, [r1, 8])
    str(r7, [r6, 8])
    ldr(r7, [r1, 12])
    str(r7, [r6, 12])
    add(r1, 16)
    add(r6, 16)
    sub(r5, 4)
    bgt(words)
    add(r0, r0, r4)
    sub(r2, 1)
    bgt(row)
    pop({r0})
