# SPDX-FileCopyrightText: 2026 John Park with Claude Opus 5.5 for Adafruit Industries
#
# SPDX-License-Identifier: MIT
"""Desktop stand-in for turbo_source/mem.py: there are no real addresses here."""

SRAM = 0x20000000


def address(buf):
    return 0


def zero(buf, words):
    memoryview(buf).cast("B")[: 4 * words] = bytes(4 * words)
