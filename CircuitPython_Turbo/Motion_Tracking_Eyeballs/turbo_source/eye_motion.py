# SPDX-FileCopyrightText: 2026 phillip torrone for Adafruit Industries
#
# SPDX-License-Identifier: MIT
"""How much each part of the camera image changed since the last frame.

``current`` is the frame just decoded and ``previous`` the one before it.
Both are 160x120 pixels of RGB565 with the high byte first (the order jpegio
decodes into, ``RGB565_SWAPPED``), 38,400 bytes each. ``previous`` must be
writable: each pixel of ``current`` is copied into it as it is read, so it's
ready for the next frame. ``stats`` receives the results:

====== ====================================================================
bytes  contents
====== ====================================================================
0      mean brightness (0-255) of the current frame
1      mean brightness change per pixel
2      number of zones whose mean change is 12 or more
3      always 0
4-5    pixels whose brightness changed by 24 or more (little-endian)
6-7    mean x of those pixels, or 65535 if there are none (little-endian)
8-9    mean y of those pixels, or 65535 if there are none (little-endian)
10-11  always 0
12-15  total brightness change, all pixels (little-endian)
16-207 the 16x12 zone grid, row by row: each zone is a 10x10 pixel square,
       and its value is the mean brightness change of its 100 pixels
====== ====================================================================

"""

import array

import micropython
from micropython import const

_WIDTH = const(160)
_HEIGHT = const(120)
_FRAME_BYTES = const(38400)  # 160 x 120 pixels x 2 bytes
_STATS_BYTES = const(208)
_ZONES = const(192)  # 16 x 12 zones of 10 x 10 pixels
_CHANGED = const(24)  # a pixel counts as changed at this brightness change
_ACTIVE = const(12)  # a zone counts as active at this mean change

# Work space for the Viper kernel, allocated once so calls make no garbage:
# entries 0-191 are the zone totals, then the totals process() finishes in
# Python (Viper has no division).
_W_TOTAL = const(192)  # sum of the brightness of every current pixel
_W_DIFFERENCE = const(193)  # sum of every pixel's brightness change
_W_CHANGED = const(194)  # number of changed pixels
_W_SUM_X = const(195)  # sum of the x of the changed pixels
_W_SUM_Y = const(196)  # sum of the y of the changed pixels
_W_ACTIVE = const(197)  # number of active zones
_work = array.array("I", [0] * 198)

# pylint: disable=too-many-locals, undefined-variable, too-many-statements
@micropython.viper
def _compare(prev: ptr8, cur: ptr8, stats: ptr8, work: ptr32):
    """The per-pixel work. Viper rules: every variable is an int or a
    pointer, nothing is range checked, and integers wrap silently. The
    largest total here is 19,200 pixels x 255 = 4,896,000, well inside 32
    bits, and every index is bounded by the fixed 160x120 loops."""
    zone = 0
    while zone < _ZONES:
        work[zone] = 0
        zone += 1
    total = 0
    difference = 0
    changed = 0
    sum_x = 0
    sum_y = 0

    i = 0  # byte offset of the pixel: 2 bytes per pixel
    band = 0  # first zone of the current band of 10 rows
    rows_in_band = 0
    y = 0
    while y < _HEIGHT:
        zone = band
        columns_in_zone = 0
        x = 0
        while x < _WIDTH:
            # Brightness of the new pixel. RGB565 has 5 bits of red, 6 of
            # green and 5 of blue; each is widened to 8 bits by repeating its
            # top bits, then weighted 77:150:29 (the usual luma weights,
            # out of 256).
            hi = cur[i]
            lo = cur[i + 1]
            v = (hi << 8) | lo
            r = v >> 11
            g = (v >> 5) & 63
            b = v & 31
            now = (
                77 * ((r << 3) | (r >> 2))
                + 150 * ((g << 2) | (g >> 4))
                + 29 * ((b << 3) | (b >> 2))
            ) >> 8

            # The same for the old pixel
            v = (prev[i] << 8) | prev[i + 1]
            r = v >> 11
            g = (v >> 5) & 63
            b = v & 31
            old = (
                77 * ((r << 3) | (r >> 2))
                + 150 * ((g << 2) | (g >> 4))
                + 29 * ((b << 3) | (b >> 2))
            ) >> 8

            d = now - old
            if d < 0:
                d = 0 - d
            total += now
            difference += d
            work[zone] += d
            if d >= _CHANGED:
                changed += 1
                sum_x += x
                sum_y += y

            # Keep this pixel for the next frame.
            prev[i] = hi
            prev[i + 1] = lo

            i += 2
            x += 1
            columns_in_zone += 1
            if columns_in_zone == 10:
                columns_in_zone = 0
                zone += 1
        y += 1
        rows_in_band += 1
        if rows_in_band == 10:
            rows_in_band = 0
            band += 16

    # Zone means. Viper can't divide, so n // 100 is (n * 5243) >> 19, which
    # gives exactly the same result for every zone total possible here
    # (0 to 25,500).
    active = 0
    zone = 0
    while zone < _ZONES:
        mean = (work[zone] * 5243) >> 19
        stats[16 + zone] = mean
        if mean >= _ACTIVE:
            active += 1
        zone += 1

    work[_W_TOTAL] = total
    work[_W_DIFFERENCE] = difference
    work[_W_CHANGED] = changed
    work[_W_SUM_X] = sum_x
    work[_W_SUM_Y] = sum_y
    work[_W_ACTIVE] = active


@micropython.viper
def _address(buf: ptr8) -> uint:
    """Where a buffer's bytes start in memory, to check for overlaps."""
    return uint(buf)


def _overlap(a, a_len, b, b_len):
    start_a = _address(a)
    start_b = _address(b)
    return start_a < start_b + b_len and start_b < start_a + a_len


def _put16(stats, offset, value):
    stats[offset] = value & 0xFF
    stats[offset + 1] = value >> 8


def process(previous, current, stats):
    """Compare ``current`` with ``previous``, write the results into
    ``stats``, and copy ``current`` into ``previous``."""
    # Viper does no checking of its own, so check everything first: a wrong
    # length or overlapping buffers would write over other memory.
    if len(previous) != _FRAME_BYTES or len(current) != _FRAME_BYTES:
        raise ValueError("previous and current must be 38,400 bytes")
    if len(stats) != _STATS_BYTES:
        raise ValueError("stats must be 208 bytes")
    if (
        _overlap(previous, _FRAME_BYTES, current, _FRAME_BYTES)
        or _overlap(previous, _FRAME_BYTES, stats, _STATS_BYTES)
        or _overlap(current, _FRAME_BYTES, stats, _STATS_BYTES)
    ):
        raise ValueError("buffers must not overlap")
    # Raises TypeError for read-only buffers such as bytes, before Viper
    # writes into them.
    previous[0] = previous[0]
    stats[0] = 0

    work = _work
    _compare(previous, current, stats, work)

    # The few divisions, in plain Python
    changed = work[_W_CHANGED]
    difference = work[_W_DIFFERENCE]
    stats[0] = work[_W_TOTAL] // 19200
    stats[1] = difference // 19200
    stats[2] = work[_W_ACTIVE]
    stats[3] = 0
    _put16(stats, 4, changed)
    _put16(stats, 6, work[_W_SUM_X] // changed if changed else 65535)
    _put16(stats, 8, work[_W_SUM_Y] // changed if changed else 65535)
    stats[10] = stats[11] = 0
    stats[12] = difference & 0xFF
    stats[13] = (difference >> 8) & 0xFF
    stats[14] = (difference >> 16) & 0xFF
    stats[15] = difference >> 24
