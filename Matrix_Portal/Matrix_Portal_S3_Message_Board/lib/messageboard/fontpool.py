# SPDX-FileCopyrightText: 2023 Melissa LeBlanc-Williams for Adafruit Industries
#
# SPDX-License-Identifier: MIT

import terminalio
from adafruit_bitmap_font import bitmap_font


class FontPool:
    def __init__(self):
        """Create a pool of fonts for reuse to avoid loading duplicates"""
        self._fonts = {}
        self.add_font("terminal")

    def add_font(self, name, file=None):
        if name in self._fonts:
            return
        if name == "terminal":
            font = terminalio.FONT
        else:
            font = bitmap_font.load_font(file)
        self._fonts[name] = font

    def find_font(self, name):
        if name in self._fonts:
            return self._fonts[name]
        return None
