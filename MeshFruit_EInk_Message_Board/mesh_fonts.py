# SPDX-FileCopyrightText: 2026 Pedro Ruiz for Adafruit Industries
#
# SPDX-License-Identifier: MIT

"""Bitmap font loading and the size rules the layout depends on."""

import terminalio
from adafruit_display_text import wrap_text_to_pixels

try:
    from adafruit_bitmap_font import bitmap_font
except ImportError:
    bitmap_font = None

WIDTH = 400
MARGIN = 10
TEXT_WIDTH = WIDTH - MARGIN * 2


# Colour carries recency: the newest message is red, older ones black.
# Size carries fit: a long newest message drops to the medium face so
# it does not crowd everything else off the panel.
# All three faces are from the public domain Misc-Fixed family.
# Weight carries recency (bold = newest), size carries fit.
FONT_PATHS = {
    "large_bold": "/fonts/9x18B.pcf",
    "medium_bold": "/fonts/7x14B.pcf",
    "medium": "/fonts/7x14.pcf",
    "name": "/fonts/6x13B.pcf",
    "small": "/fonts/6x10.pcf",
}


MAX_LARGE_LINES = 2


def load_font(path):
    """Load a bitmap font, or return None if it is unavailable."""
    if bitmap_font is None:
        return None
    try:
        return bitmap_font.load_font(path)
    except (OSError, ValueError) as error:
        print("font", path, "unavailable:", error)
        return None


FONTS = {name: load_font(path) for name, path in FONT_PATHS.items()}

# Fall back to the built-in face so the board still runs with no font
# files installed. terminalio.FONT has no bold or intermediate size, so
# the fallback leans on scale alone.


# Fall back to the built-in face so the board still runs with no font
# files installed. terminalio.FONT has no bold or intermediate size, so
# the fallback leans on scale alone.
FALLBACK = {
    "large_bold": (terminalio.FONT, 2, 26),
    "medium_bold": (terminalio.FONT, 1, 14),
    "medium": (terminalio.FONT, 1, 14),
    "name": (terminalio.FONT, 1, 14),
    "small": (terminalio.FONT, 1, 12),
}


def face(size):
    """Return (font, scale, line_height) for a named face."""
    font = FONTS.get(size)
    if font is not None:
        return font, 1, font.get_bounding_box()[1] + 4
    return FALLBACK.get(size, FALLBACK["medium"])


def wrap_for(text, size):
    """Wrap text to the panel width for a named size."""
    font, scale, line_height = face(size)
    lines = wrap_text_to_pixels(text, TEXT_WIDTH // scale, font)
    return lines, font, scale, line_height


def size_for(index, text):
    """Pick a face for a message at this position in the list.

    The newest message is always bold and red. It uses the large face
    unless it runs long, in which case it steps down to the medium
    bold face so it does not crowd older messages off the panel.
    """
    if index != 0:
        return "medium"
    lines, _, _, _ = wrap_for(text, "large_bold")
    if len(lines) > MAX_LARGE_LINES:
        return "medium_bold"
    return "large_bold"
