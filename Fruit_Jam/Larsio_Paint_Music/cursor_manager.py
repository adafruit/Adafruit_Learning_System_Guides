# SPDX-FileCopyrightText: 2025 John Park and Claude AI for Adafruit Industries
#
# SPDX-License-Identifier: MIT
"""
# cursor_manager.py: CircuitPython Music Staff Application component
"""

# pylint: disable=import-error
from displayio import Bitmap, Palette, TileGrid


# pylint: disable=invalid-name,no-member,too-many-instance-attributes
# pylint: disable=too-many-arguments,too-many-branches,too-many-statements
class CursorManager:
    """Manages cursor appearance and position"""

    def __init__(self, bg_color=0x8AAD8A):
        self.bg_color = bg_color

        # Cursors
        self.crosshair_cursor = None
        self.triangle_cursor = None
        self.current_cursor = None

        self.create_cursors()

    def create_cursors(self):
        """Create custom cursor bitmaps for different areas"""
        # Regular crosshair cursor for staff area
        crosshair_cursor_bitmap = Bitmap(8, 8, 2)
        crosshair_cursor_palette = Palette(2)
        crosshair_cursor_palette[0] = self.bg_color  # Background color (sage green)
        crosshair_cursor_palette[1] = 0x000000  # Cursor color (black)
        crosshair_cursor_palette.make_transparent(0)  # Make background transparent

        for i in range(8):
            crosshair_cursor_bitmap[i, 3] = 1
            crosshair_cursor_bitmap[i, 4] = 1
            crosshair_cursor_bitmap[3, i] = 1
            crosshair_cursor_bitmap[4, i] = 1

        # Triangle cursor for controls area
        triangle_cursor_bitmap = Bitmap(12, 12, 2)
        triangle_cursor_palette = Palette(2)
        triangle_cursor_palette[0] = 0x000000  # Background color
        triangle_cursor_palette[1] = 0x000000  # Cursor color (black)
        triangle_cursor_palette.make_transparent(0)  # Make background transparent

        # Draw a triangle cursor
        for y in range(12):
            width = y // 2 + 1  # Triangle gets wider as y increases
            for x in range(width):
                triangle_cursor_bitmap[x, y] = 1

        # Create a TileGrid for each cursor type
        self.crosshair_cursor = TileGrid(
            crosshair_cursor_bitmap,
            pixel_shader=crosshair_cursor_palette
        )
        self.triangle_cursor = TileGrid(
            triangle_cursor_bitmap,
            pixel_shader=triangle_cursor_palette
        )

        # Initially use crosshair cursor
        self.current_cursor = self.crosshair_cursor
        self.triangle_cursor.hidden = True

        return self.crosshair_cursor, self.triangle_cursor

    def set_cursor_position(self, x, y):
        """Set the position of the current cursor"""
        self.current_cursor.x = x
        self.current_cursor.y = y

    def switch_cursor(self, use_triangle=False):
        """Switch between crosshair and triangle cursor"""
        if use_triangle and self.current_cursor != self.triangle_cursor:
            self.crosshair_cursor.hidden = True
            self.triangle_cursor.hidden = False
            self.current_cursor = self.triangle_cursor
        elif not use_triangle and self.current_cursor != self.crosshair_cursor:
            self.triangle_cursor.hidden = True
            self.crosshair_cursor.hidden = False
            self.current_cursor = self.crosshair_cursor
