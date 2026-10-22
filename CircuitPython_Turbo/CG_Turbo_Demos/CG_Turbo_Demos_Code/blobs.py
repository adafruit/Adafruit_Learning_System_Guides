# SPDX-FileCopyrightText: 2026 John Park with Claude Opus 5.5 for Adafruit Industries
#
# SPDX-License-Identifier: MIT
"""The metaballs' motion: Lissajous paths, shared by the demo and the desktop tools."""

import math

# (radius, x speed, y speed, phase) per ball: the first six, then more made
# the same way, up to MAX
PATHS = [
    (46, 0.31, 0.43, 0.0),
    (38, 0.47, 0.29, 1.3),
    (54, 0.23, 0.37, 2.1),
    (32, 0.53, 0.61, 3.7),
    (42, 0.41, 0.19, 4.4),
    (28, 0.67, 0.49, 5.2),
]
MAX = 10  # more misses 30 fps once flip and Python are counted (11: ~25 fps)
for _i in range(len(PATHS), MAX):
    PATHS.append(
        (
            26 + (_i * 17) % 28,
            0.2 + (_i * 0.137) % 0.5,
            0.2 + (_i * 0.211) % 0.45,
            (_i * 2.39) % 6.28,
        )
    )
START = 6
SPEED = 0.9  # how fast the balls move along their paths


def positions(t, width, height, count=START):
    """(x, y, radius) of the first count balls at time t seconds."""
    t *= SPEED
    balls = []
    for r, sx, sy, phase in PATHS[:count]:
        x = width / 2 + (width / 2 - r * 0.6) * math.sin(t * sx * 2 + phase)
        y = height / 2 + (height / 2 - r * 0.6) * math.sin(t * sy * 2 + phase * 1.7)
        balls.append((x, y, r))
    return balls
