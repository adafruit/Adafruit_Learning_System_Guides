# SPDX-FileCopyrightText: Copyright (c) 2026 Tim Cocks for Adafruit Industries
#
# SPDX-License-Identifier: MIT
"""Maidenhead grid locators <-> latitude and longitude, and distances.

    to_latlon('EM28')          -> (38.5, -95.0): the centre of the square
    to_latlon('EM28pv')        -> the centre of the subsquare
    bounds('EM28')             -> (south, west, north, east)
    from_latlon(38.9, -94.6)   -> 'EM28pv' (precision: 2, 4, 6 or 8 characters)
    is_grid('EM28')            -> True ('RR73', an FT8 sign-off, is not a grid)
    distance_km(a, b), great_circle(a, b, n): between two (lat, lon)

A locator is pairs of letters and digits, each pair splitting the one
before: fields (AA-RR, 20 x 10 degrees of longitude x latitude), squares
(00-99, 2 x 1 degrees), subsquares (aa-xx, 5 x 2.5 minutes) and extended
squares (00-99, 30 x 15 seconds). FT8 messages carry 4 characters: a
square, about 170 x 110 km at 40 degrees north.

Plain Python: the same code runs on CircuitPython and on a PC.
"""
import math

# pylint: disable=too-many-locals

EARTH_KM = 6371.0
# (longitude, latitude) units per character pair, in 1/120 and 1/240
# degree (an extended square), and how many values each character has.
_PAIRS = ((2400, 2400, 18, 'A'), (240, 240, 10, '0'), (10, 10, 24, 'A'), (1, 1, 10, '0'))


def _index(ch, base, count):
    k = ord(ch) - ord(base)
    if not 0 <= k < count:
        raise ValueError('not a Maidenhead locator character: %r' % ch)
    return k


def bounds(grid):
    """The (south, west, north, east) edges of a 2, 4, 6 or 8 character
    locator (any case), in degrees."""
    g = grid.strip().upper()
    if len(g) not in (2, 4, 6, 8):
        raise ValueError('a Maidenhead locator has 2, 4, 6 or 8 characters: %r' % grid)
    x = y = 0
    for k in range(len(g) // 2):
        size_x, size_y, count, base = _PAIRS[k]
        x += _index(g[2 * k], base, count) * size_x
        y += _index(g[2 * k + 1], base, count) * size_y
    size_x, size_y = _PAIRS[len(g) // 2 - 1][:2]
    return (y / 240 - 90, x / 120 - 180, (y + size_y) / 240 - 90, (x + size_x) / 120 - 180)


def to_latlon(grid):
    """The centre of a locator, as (lat, lon) in degrees."""
    s, w, n, e = bounds(grid)
    return (s + n) / 2, (w + e) / 2


def from_latlon(lat, lon, precision=6):
    """The locator (precision characters: 2, 4, 6 or 8) of the square that
    (lat, lon) is in; the subsquare in lower case ('EM28pv')."""
    if precision not in (2, 4, 6, 8):
        raise ValueError('precision is 2, 4, 6 or 8')
    # In extended squares from the south-west corner of the world.
    x = min(43199, max(0, int(((lon + 180) % 360) * 120)))
    y = min(43199, max(0, int((lat + 90) * 240)))
    out = ''
    for size_x, size_y, count, base in _PAIRS[:precision // 2]:
        out += chr(ord(base) + x // size_x % count) + chr(ord(base) + y // size_y % count)
    return out[:4] + out[4:6].lower() + out[6:]


def is_grid(word):
    """True if word is a 4 or 6 character locator as FT8 messages send
    them (upper case). 'RR73' is FT8's sign-off, not the grid in the
    Arctic."""
    if len(word) not in (4, 6) or word == 'RR73':
        return False
    if not ('A' <= word[0] <= 'R' and 'A' <= word[1] <= 'R' and word[2:4].isdigit()):
        return False
    return len(word) == 4 or ('A' <= word[4] <= 'X' and 'A' <= word[5] <= 'X')


def distance_km(a, b):
    """Great circle distance between (lat, lon) a and b."""
    lat1, lon1 = math.radians(a[0]), math.radians(a[1])
    lat2, lon2 = math.radians(b[0]), math.radians(b[1])
    h = (math.sin((lat2 - lat1) / 2) ** 2
         + math.cos(lat1) * math.cos(lat2) * math.sin((lon2 - lon1) / 2) ** 2)
    return 2 * EARTH_KM * math.asin(min(1.0, math.sqrt(h)))


def great_circle(a, b, n=16):
    """n + 1 points (lat, lon) along the great circle from a to b. The
    longitudes run on without a jump at the 180th meridian (they can go
    past -180 or 180), so the points can be joined by straight lines."""
    lat1, lon1 = math.radians(a[0]), math.radians(a[1])
    lat2, lon2 = math.radians(b[0]), math.radians(b[1])
    d = distance_km(a, b) / EARTH_KM
    if d < 1e-6:
        return [a, b]
    ax, ay, az = math.cos(lat1) * math.cos(lon1), math.cos(lat1) * math.sin(lon1), math.sin(lat1)
    bx, by, bz = math.cos(lat2) * math.cos(lon2), math.cos(lat2) * math.sin(lon2), math.sin(lat2)
    sd = math.sin(d)
    pts = []
    prev = None
    for i in range(n + 1):
        f = i / n
        p = math.sin((1 - f) * d) / sd
        q = math.sin(f * d) / sd
        x, y, z = p * ax + q * bx, p * ay + q * by, p * az + q * bz
        lon = math.degrees(math.atan2(y, x))
        if prev is not None:
            lon = prev + (lon - prev + 180) % 360 - 180
        prev = lon
        pts.append((math.degrees(math.atan2(z, math.sqrt(x * x + y * y))), lon))
    return pts
