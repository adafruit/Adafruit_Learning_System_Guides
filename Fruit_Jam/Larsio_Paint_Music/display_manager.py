# SPDX-FileCopyrightText: 2025 John Park and Claude AI for Adafruit Industries
#
# SPDX-License-Identifier: MIT
"""
# display_manager.py: CircuitPython Music Staff Application component
"""
# pylint: disable=import-error,invalid-name,no-member,too-many-instance-attributes,too-many-arguments,too-many-branches,too-many-statements

import supervisor
import displayio
from adafruit_fruitjam.peripherals import request_display_config



class DisplayManager:
    """Manages the display initialization and basic display operations"""


    def __init__(self, width=320, height=240):
        self.SCREEN_WIDTH = width
        self.SCREEN_HEIGHT = height
        self.display = None
        self.main_group = None

    def initialize_display(self):
        """Initialize the DVI display"""
        # Use the Fruit Jam library to set up display, that way on DAC fallback
        # the display doesn't attempt to be re-initialized

        request_display_config(self.SCREEN_WIDTH, self.SCREEN_HEIGHT,color_depth=16)

        # Create the display
        self.display = supervisor.runtime.display

        # Create main group
        self.main_group = displayio.Group()

        # Set the display's root group
        self.display.root_group = self.main_group

        return self.main_group, self.display

    def create_background(self, color=0x888888):
        """Create a background with the given color"""
        bg_bitmap = displayio.Bitmap(self.SCREEN_WIDTH, self.SCREEN_HEIGHT, 1)
        bg_palette = displayio.Palette(1)
        bg_palette[0] = color

        # Fill the bitmap with the background color
        for x in range(self.SCREEN_WIDTH):
            for y in range(self.SCREEN_HEIGHT):
                bg_bitmap[x, y] = 0

        # Create a TileGrid with the background bitmap
        bg_grid = displayio.TileGrid(bg_bitmap, pixel_shader=bg_palette, x=0, y=0)

        return bg_grid
