# SPDX-FileCopyrightText: 2026 John Park with Claude Opus 5.5 for Adafruit Industries
#
# SPDX-License-Identifier: MIT
"""Small memory helpers."""

import micropython

SRAM = 0x20000000  # internal SRAM starts here; PSRAM is at 0x11000000


@micropython.viper
def address(buf: ptr8) -> int:
    """Where a buffer's data lives."""
    return int(buf)


@micropython.viper
def zero(buf: ptr32, words: int):
    """Clear words 32-bit words. (Slice-assigning zeros into a big bytearray
    is surprisingly slow in CircuitPython: 42 ms per 2880-byte row of the
    690 KB Cornell buffer.)"""
    while words > 0:
        buf[0] = 0
        buf = ptr32(int(buf) + 4)
        words -= 1
