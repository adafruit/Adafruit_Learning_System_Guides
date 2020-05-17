# The MIT License (MIT)
#
# Copyright (c) 2020 Jeff Epler for Adafruit Industries LLC
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
"""
Icon Bar suitable for navigation by joystick
"""

import adafruit_imageload.bmp
import displayio

def make_palette(seq):
    """Create a palette from a sequence of colors"""
    pal = displayio.Palette(len(seq))
    for i, color in enumerate(seq):
        if color is None:
            pal.make_transparent(i)
        else:
            pal[i] = color
    return pal

BLACK, WHITE, RED, BLUE = 0x111111, 0xffffff, 0xff0000, 0x0000ff

PALETTE_NORMAL = make_palette([BLACK, WHITE, BLACK, BLACK])
PALETTE_SELECTED = make_palette([BLACK, WHITE, RED, BLACK])
PALETTE_ACTIVE = make_palette([BLACK, WHITE, BLACK, BLUE])
PALETTE_BOTH = make_palette([BLACK, WHITE, RED, BLUE])
PALETTES = [PALETTE_NORMAL, PALETTE_ACTIVE, PALETTE_SELECTED, PALETTE_BOTH]

class IconBar:
    """An icon bar presents n 16x16 icons in a row.
One icon can be "selected" and any number can be "active"."""
    def __init__(self, n=8, filename="/rsrc/icons.bmp"):
        self.group = displayio.Group(max_size=n)
        self.bitmap_file = open(filename, "rb")
        self.bitmap = adafruit_imageload.bmp.load(self.bitmap_file, bitmap=displayio.Bitmap)[0]


        self._selected = None
        self.icons = [displayio.TileGrid(self.bitmap,
                                         pixel_shader=PALETTE_NORMAL, x=16*i,
                                         y=0, width=1, height=1,
                                         tile_width=16, tile_height=16)
                      for i in range(n)]
        self.active = [False] * n

        for i, icon in enumerate(self.icons):
            icon[0] = i
            self.group.append(icon)
        self.select(0)

    @property
    def selected(self):
        """The currently selected icon"""
        return self._selected

    @selected.setter
    def selected(self, n):
        self.select(n)

    def select(self, n):
        """Select the n'th icon"""
        old_selected = self._selected
        self._selected = n
        if n != old_selected:
            self._refresh(n)
            if old_selected is not None:
                self._refresh(old_selected)

    def set_active(self, n, new_state):
        """Sets the n'th icon's active state to new_state"""
        new_state = bool(new_state)
        if self.active[n] == new_state:
            return
        self.active[n] = new_state
        self._refresh(n)

    def activate(self, n):
        """Set the n'th icon to be active"""
        self.set_active(n, True)

    def deactivate(self, n):
        """Set the n'th icon to be inactive"""
        self.set_active(n, False)

    def toggle(self, n):
        """Toggle the state of the n'th icon"""
        self.set_active(n, not self.active[n])
        print()

    def _refresh(self, n):
        """Update the appearance of the n'th icon"""
        palette_index = self.active[n] + 2 * (self._selected == n)
        self.icons[n].pixel_shader = PALETTES[palette_index]
