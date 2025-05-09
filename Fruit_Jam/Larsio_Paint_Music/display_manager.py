"""
# display_manager.py: CircuitPython Music Staff Application component
"""
# pylint: disable=import-error,invalid-name,no-member,too-many-instance-attributes,too-many-arguments,too-many-branches,too-many-statements

import displayio
import picodvi
import framebufferio
import board



class DisplayManager:
    """Manages the display initialization and basic display operations"""


    def __init__(self, width=320, height=240):
        self.SCREEN_WIDTH = width
        self.SCREEN_HEIGHT = height
        self.display = None
        self.main_group = None

    def initialize_display(self):
        """Initialize the DVI display"""
        # Release any existing displays
        displayio.release_displays()

        # Initialize the DVI framebuffer
        fb = picodvi.Framebuffer(self.SCREEN_WIDTH, self.SCREEN_HEIGHT,
                              clk_dp=board.CKP, clk_dn=board.CKN,
                              red_dp=board.D0P, red_dn=board.D0N,
                              green_dp=board.D1P, green_dn=board.D1N,
                              blue_dp=board.D2P, blue_dn=board.D2N,
                              color_depth=16)

        # Create the display
        self.display = framebufferio.FramebufferDisplay(fb)

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
