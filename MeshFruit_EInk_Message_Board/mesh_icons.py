# SPDX-FileCopyrightText: 2026 Pedro Ruiz for Adafruit Industries
#
# SPDX-License-Identifier: MIT

"""Weather glyphs drawn with vectorio, so no bitmap assets are needed."""

import math

import displayio
import vectorio

BLACK = 0x000000
RED = 0xFF0000
WHITE = 0xFFFFFF

black_palette = displayio.Palette(1)
black_palette[0] = BLACK

red_palette = displayio.Palette(1)
red_palette[0] = RED

white_palette = displayio.Palette(1)
white_palette[0] = WHITE


def icon_cloud(group, cx, cy, palette=None):
    """Three lobes over a slab, which reads as a cloud at this size."""
    shader = palette or black_palette
    group.append(vectorio.Circle(pixel_shader=shader, radius=9, x=cx - 8, y=cy))
    group.append(vectorio.Circle(pixel_shader=shader, radius=12, x=cx + 4, y=cy - 3))
    group.append(vectorio.Circle(pixel_shader=shader, radius=8, x=cx + 16, y=cy + 1))
    group.append(
        vectorio.Rectangle(
            pixel_shader=shader, width=32, height=10, x=cx - 10, y=cy
        )
    )


def icon_sun(group, cx, cy, radius=13, palette=None):
    """Filled disc with four spokes."""
    shader = palette or black_palette
    group.append(vectorio.Circle(pixel_shader=shader, radius=radius, x=cx, y=cy))
    reach = radius + 7
    for dx, dy, wide, high in (
        (-1, -reach, 3, 6),
        (-1, reach - 5, 3, 6),
        (-reach, -1, 6, 3),
        (reach - 5, -1, 6, 3),
    ):
        group.append(
            vectorio.Rectangle(
                pixel_shader=shader, width=wide, height=high,
                x=cx + dx, y=cy + dy,
            )
        )


def icon_drops(group, cx, cy, palette=None, count=3):
    """Short slanted strokes under a cloud."""
    shader = palette or black_palette
    for index in range(count):
        left = cx - 10 + index * 12
        group.append(
            vectorio.Polygon(
                pixel_shader=shader,
                points=[(0, 0), (4, 0), (0, 9), (-4, 9)],
                x=left,
                y=cy,
            )
        )


def icon_bolt(group, cx, cy):
    """Lightning, in red so severe weather carries the accent colour."""
    group.append(
        vectorio.Polygon(
            pixel_shader=red_palette,
            points=[(8, 0), (0, 12), (5, 12), (-2, 24), (12, 9), (6, 9), (13, 0)],
            x=cx - 4,
            y=cy,
        )
    )


def draw_weather_icon(group, code, cx, cy, color=BLACK):
    """Pick an icon for a WMO weather code."""
    shader = red_palette if color == RED else black_palette

    if code == 0:
        icon_sun(group, cx, cy + 6, palette=shader)
    elif code in (1, 2):
        icon_sun(group, cx - 8, cy - 4, radius=9, palette=shader)
        icon_cloud(group, cx + 2, cy + 8, palette=shader)
    elif code == 3:
        icon_cloud(group, cx - 4, cy + 4, palette=shader)
    elif code in (45, 48):
        for row in range(3):
            group.append(
                vectorio.Rectangle(
                    pixel_shader=shader,
                    width=40 - row * 6,
                    height=5,
                    x=cx - 18 + row * 3,
                    y=cy - 6 + row * 12,
                )
            )
    elif code in (71, 73, 75, 77, 85, 86):
        icon_cloud(group, cx - 4, cy - 4, palette=shader)
        for index in range(3):
            group.append(
                vectorio.Circle(
                    pixel_shader=shader,
                    radius=3,
                    x=cx - 12 + index * 12,
                    y=cy + 20,
                )
            )
    elif code in (95, 96, 99):
        icon_cloud(group, cx - 4, cy - 6, palette=shader)
        icon_bolt(group, cx, cy + 8)
    else:
        # every drizzle, rain and shower code
        icon_cloud(group, cx - 4, cy - 6, palette=shader)
        icon_drops(group, cx, cy + 10, palette=shader)


def icon_moon(group, cx, cy, phase, radius=9):
    """Disc with a white disc slid across it to carve the lit portion."""
    lit = (1 - math.cos(2 * math.pi * phase)) / 2
    group.append(
        vectorio.Circle(pixel_shader=black_palette, radius=radius, x=cx, y=cy)
    )
    direction = 1 if phase < 0.5 else -1
    offset = int(direction * 2 * radius * lit)
    group.append(
        vectorio.Circle(
            pixel_shader=white_palette, radius=radius - 1, x=cx + offset, y=cy
        )
    )


def icon_sun_marker(group, cx, cy, rising):
    """Small half sun with an arrow, marking rise or set."""
    group.append(
        vectorio.Circle(pixel_shader=black_palette, radius=5, x=cx, y=cy - 1)
    )
    group.append(
        vectorio.Rectangle(
            pixel_shader=black_palette, width=16, height=2, x=cx - 8, y=cy + 5
        )
    )
    if rising:
        # Arrow sits above the disc, pointing up out of the horizon.
        points = [(0, 0), (4, 5), (-4, 5)]
        arrow_y = cy - 14
    else:
        # Arrow drops below the horizon line, pointing down.
        points = [(0, 5), (4, 0), (-4, 0)]
        arrow_y = cy + 8
    group.append(
        vectorio.Polygon(
            pixel_shader=black_palette, points=points, x=cx, y=arrow_y
        )
    )
