# SPDX-FileCopyrightText: 2026 John Park with Claude Opus 5.5 for Adafruit Industries
#
# SPDX-License-Identifier: MIT
"""Viper kernels for the framebuffer benchmark (step 2).

Compiled with mpy-cross -march=armv7emsp into lib/fbtest.mpy. Every kernel
takes its buffers as pointers and its settings in one ptr32 args array, the
way Adafruit's Turbo examples do.
"""

import micropython
from micropython import const

# args slots shared by the kernels
ARG_WIDTH = const(0)
ARG_HEIGHT = const(1)
ARG_TIME = const(2)
ARG_COLOR = const(3)
ARG_COUNT = const(4)
ARGS_LEN = const(5)


@micropython.viper
def address(buf: ptr8) -> int:
    """Where a buffer's data lives: 0x2... is internal SRAM, 0x1... is PSRAM."""
    return int(buf)


@micropython.viper
def fill16(dest: ptr16, args: ptr32):
    """One RGB565 store per pixel."""
    n = args[ARG_COUNT]
    color = args[ARG_COLOR]
    i = 0
    while i < n:
        dest[i] = color
        i += 1


@micropython.viper
def fill32(dest: ptr32, args: ptr32):
    """Two pixels per store."""
    n = args[ARG_COUNT] >> 1
    color = args[ARG_COLOR] & 0xFFFF
    pair = color | (color << 16)
    i = 0
    while i < n:
        dest[i] = pair
        i += 1


@micropython.viper
def copy32(dest: ptr32, src: ptr32, args: ptr32):
    """Word copy loop, to compare against memoryview slice assignment."""
    n = args[ARG_COUNT] >> 1
    i = 0
    while i < n:
        dest[i] = src[i]
        i += 1


@micropython.viper
def pattern(dest: ptr16, args: ptr32):
    """A moving XOR pattern: a few integer ops per pixel, like a cheap shader."""
    w = args[ARG_WIDTH]
    h = args[ARG_HEIGHT]
    t = args[ARG_TIME]
    i = 0
    y = 0
    while y < h:
        x = 0
        yt = y + t
        while x < w:
            v = (x ^ yt) + t
            dest[i] = ((v & 0x1F) << 11) | (((x + t) & 0x3F) << 5) | ((y - t) & 0x1F)
            i += 1
            x += 1
        y += 1


# Only the first two locals of a viper function live in registers (here the
# first two arguments); every other local is loaded from and stored to the
# stack each time it is used. The fast kernels keep the moving pointer and
# the loop counter in those two slots.


@micropython.viper
def fill32_fast(p: ptr32, n: int, color: int):
    """n pixel pairs (a multiple of 8) of the 32-bit color pair, pointer bumped."""
    while n > 0:
        p[0] = color
        p[1] = color
        p[2] = color
        p[3] = color
        p[4] = color
        p[5] = color
        p[6] = color
        p[7] = color
        p = ptr32(int(p) + 32)
        n -= 8


@micropython.viper
def pattern_fast(p: ptr32, n: int, args: ptr32):
    """pattern() two pixels per store; n is the pair count, p walks the screen."""
    w = args[ARG_WIDTH] >> 1
    t = args[ARG_TIME]
    x = 0
    y = 0
    yt = t
    while n > 0:
        x2 = x << 1
        a = x2 + t
        lo = (((x2 ^ yt) + t) & 0x1F) << 11 | (a & 0x3F) << 5 | ((y - t) & 0x1F)
        hi = ((((x2 + 1) ^ yt) + t) & 0x1F) << 11 | ((a + 1) & 0x3F) << 5 | ((y - t) & 0x1F)
        p[0] = lo | (hi << 16)
        p = ptr32(int(p) + 4)
        n -= 1
        x += 1
        if x == w:
            x = 0
            y += 1
            yt = y + t


@micropython.asm_thumb
def fill32_asm(r0, r1, r2, r3):
    # Relabelled as viper by tools/asm_to_viper.py, so the arguments arrive as
    # objects in an array at r3: fill32_asm(address, pairs, color16), all small
    # ints, pairs a multiple of 4. Returns its first argument.
    ldr(r0, [r3, 0])
    ldr(r1, [r3, 4])
    ldr(r2, [r3, 8])
    push({r0})
    asr(r0, r0, 1)
    asr(r1, r1, 1)
    asr(r2, r2, 1)
    mov(r4, r2)
    lsl(r4, r4, 16)
    orr(r2, r4)
    label(loop)
    str(r2, [r0, 0])
    str(r2, [r0, 4])
    str(r2, [r0, 8])
    str(r2, [r0, 12])
    add(r0, 16)
    sub(r1, r1, 4)
    bgt(loop)
    pop({r0})


@micropython.asm_thumb
def expand8_asm(r0, r1, r2, r3):
    # expand8_asm(dest_address, src_address, pixels, palette_address): each
    # source byte indexes a 256-entry RGB565 palette. pixels must be even.
    ldr(r0, [r3, 0])
    ldr(r1, [r3, 4])
    ldr(r2, [r3, 8])
    ldr(r3, [r3, 12])
    push({r0})
    asr(r0, r0, 1)
    asr(r1, r1, 1)
    asr(r2, r2, 1)
    asr(r3, r3, 1)
    label(loop)
    ldrb(r4, [r1, 0])
    ldrb(r5, [r1, 1])
    add(r1, r1, 2)
    lsl(r4, r4, 1)
    lsl(r5, r5, 1)
    add(r4, r4, r3)
    add(r5, r5, r3)
    ldrh(r4, [r4, 0])
    ldrh(r5, [r5, 0])
    lsl(r5, r5, 16)
    orr(r4, r5)
    str(r4, [r0, 0])
    add(r0, 4)
    sub(r2, r2, 2)
    bgt(loop)
    pop({r0})
