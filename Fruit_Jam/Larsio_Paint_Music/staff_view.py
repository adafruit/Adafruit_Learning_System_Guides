# SPDX-FileCopyrightText: 2025 John Park and Claude AI for Adafruit Industries
#
# SPDX-License-Identifier: MIT
"""
# staff_view.py: Larsio Paint Music component
"""

# pylint: disable=import-error, trailing-whitespace
from displayio import Group, Bitmap, Palette, TileGrid


# pylint: disable=invalid-name,no-member,too-many-instance-attributes,too-many-arguments
# pylint: disable=too-many-branches,too-many-statements,too-many-locals,too-many-nested-blocks
class StaffView:
    """Manages the music staff display and related elements"""

    def __init__(self, screen_width, screen_height, note_manager):
        self.SCREEN_WIDTH = screen_width
        self.SCREEN_HEIGHT = screen_height
        self.note_manager = note_manager

        # Staff dimensions
        self.TOP_MARGIN = int(self.SCREEN_HEIGHT * 0.1)
        self.BOTTOM_MARGIN = int(self.SCREEN_HEIGHT * 0.2)
        self.STAFF_HEIGHT = int((self.SCREEN_HEIGHT - self.TOP_MARGIN - self.BOTTOM_MARGIN) * 0.95)
        self.STAFF_Y_START = self.TOP_MARGIN
        self.LINE_SPACING = self.STAFF_HEIGHT // 8

        # Margins and spacing
        self.START_MARGIN = 25  # Pixels from left edge for the double bar

        # Note spacing
        self.EIGHTH_NOTE_SPACING = self.SCREEN_WIDTH // 40
        self.QUARTER_NOTE_SPACING = self.EIGHTH_NOTE_SPACING * 2

        # Measure settings
        self.NOTES_PER_MEASURE = 4
        self.MEASURE_WIDTH = self.QUARTER_NOTE_SPACING * self.NOTES_PER_MEASURE
        self.MEASURES_PER_LINE = 4

        # Playback elements
        self.playhead = None
        self.highlight_grid = None

        # X positions for notes
        self.x_positions = []
        self._generate_x_positions()

    def _generate_x_positions(self):
        """Generate horizontal positions for notes"""
        self.x_positions = []
        for measure in range(self.MEASURES_PER_LINE):
            measure_start = self.START_MARGIN + (measure * self.MEASURE_WIDTH)
            for eighth_pos in range(8):
                x_pos = (measure_start + (eighth_pos * self.EIGHTH_NOTE_SPACING) +
                         self.EIGHTH_NOTE_SPACING // 2)
                if x_pos < self.SCREEN_WIDTH:
                    self.x_positions.append(x_pos)

        # Share positions with note manager
        self.note_manager.x_positions = self.x_positions

    def create_staff(self):
        """Create the staff with lines and background"""
        staff_group = Group()

        # Create staff background
        staff_bg_bitmap = Bitmap(self.SCREEN_WIDTH, self.STAFF_HEIGHT, 2)
        staff_bg_palette = Palette(2)
        staff_bg_palette[0] = 0xF5F5DC  # Light beige (transparent)
        staff_bg_palette[1] = 0x657c95 # 8AAD8A

        # Fill staff background with sage green
        for x in range(self.SCREEN_WIDTH):
            for y in range(self.STAFF_HEIGHT):
                staff_bg_bitmap[x, y] = 1

        # Create a TileGrid for staff background
        staff_bg_grid = TileGrid(
            staff_bg_bitmap,
            pixel_shader=staff_bg_palette,
            x=0,
            y=self.STAFF_Y_START
        )
        staff_group.append(staff_bg_grid)

        # Create staff lines
        staff_bitmap = Bitmap(self.SCREEN_WIDTH, self.STAFF_HEIGHT, 4)
        staff_palette = Palette(4)
        staff_palette[0] = 0x657c95  #
        staff_palette[1] = 0x000000  # Black for horizontal staff lines
        staff_palette[2] = 0x888888  # Medium gray for measure bar lines
        staff_palette[3] = 0xAAAAAA  # Lighter gray for quarter note dividers

        # Draw 5 horizontal staff lines
        for i in range(5):
            y_pos = (i + 1) * self.LINE_SPACING
            for x in range(self.SCREEN_WIDTH):
                staff_bitmap[x, y_pos] = 1

        # Add double bar at the beginning
        for x in range(self.START_MARGIN - 5, self.START_MARGIN - 2):
            for y in range(self.STAFF_HEIGHT):
                if self.LINE_SPACING <= y <= 5 * self.LINE_SPACING:
                    staff_bitmap[x, y] = 1

        for x in range(self.START_MARGIN - 1, self.START_MARGIN + 2):
            for y in range(self.STAFF_HEIGHT):
                if self.LINE_SPACING <= y <= 5 * self.LINE_SPACING:
                    staff_bitmap[x, y] = 1

        # Add measure bar lines (thicker, darker)
        bar_line_width = 2

        # For each measure (except after the last one)
        for i in range(1, self.MEASURES_PER_LINE):
            # Calculate measure bar position
            measure_bar_x = self.START_MARGIN + (i * self.MEASURE_WIDTH)

            if measure_bar_x < self.SCREEN_WIDTH:
                # Draw the measure bar line
                for y in range(self.STAFF_HEIGHT):
                    if self.LINE_SPACING <= y <= 5 * self.LINE_SPACING:
                        for thickness in range(bar_line_width):
                            if measure_bar_x + thickness < self.SCREEN_WIDTH:
                                staff_bitmap[measure_bar_x + thickness, y] = 2

        # Add quarter note divider lines within each measure
        for measure in range(self.MEASURES_PER_LINE):
            measure_start_x = self.START_MARGIN + (measure * self.MEASURE_WIDTH)

            # Calculate quarter note positions (divide measure into 4 equal parts)
            quarter_width = self.MEASURE_WIDTH // 4

            # Draw lines at the first, second, and third quarter positions
            for q in range(1, 4):  # Draw at positions 1, 2, and 3 (not at 0 or 4)
                quarter_x = measure_start_x + (q * quarter_width)

                if quarter_x < self.SCREEN_WIDTH:
                    for y in range(self.STAFF_HEIGHT):
                        if self.LINE_SPACING <= y <= 5 * self.LINE_SPACING:
                            staff_bitmap[quarter_x, y] = 3  # Use color 3 (light gray)

        # Add double bar line at the end
        double_bar_width = 5
        double_bar_x = self.START_MARGIN + (self.MEASURES_PER_LINE * self.MEASURE_WIDTH) + 5
        if double_bar_x + double_bar_width < self.SCREEN_WIDTH:
            # First thick line
            for x in range(3):
                for y in range(self.STAFF_HEIGHT):
                    if self.LINE_SPACING <= y <= 5 * self.LINE_SPACING:
                        staff_bitmap[double_bar_x + x, y] = 1

            # Second thick line (with gap)
            for x in range(3):
                for y in range(self.STAFF_HEIGHT):
                    if self.LINE_SPACING <= y <= 5 * self.LINE_SPACING:
                        staff_bitmap[double_bar_x + x + 4, y] = 1

        # Create a TileGrid with the staff bitmap
        staff_grid = TileGrid(
            staff_bitmap,
            pixel_shader=staff_palette,
            x=0,
            y=self.STAFF_Y_START
        )
        staff_group.append(staff_grid)

        return staff_group

    def create_grid_lines(self):
        """Add vertical grid lines to show note spacing"""
        grid_bitmap = Bitmap(self.SCREEN_WIDTH, self.STAFF_HEIGHT, 2)
        grid_palette = Palette(2)
        grid_palette[0] = 0x657c95  # Transparent
        grid_palette[1] = 0xAAAAAA  # Faint grid lines (light gray)

        # Draw vertical grid lines at each eighth note position
        for x_pos in self.x_positions:
            for y in range(self.STAFF_HEIGHT):
                if self.LINE_SPACING <= y <= 5 * self.LINE_SPACING:
                    grid_bitmap[x_pos, y] = 1

        return TileGrid(grid_bitmap, pixel_shader=grid_palette, x=0, y=self.STAFF_Y_START)

    def create_playhead(self):
        """Create a playhead indicator"""
        playhead_bitmap = Bitmap(2, self.STAFF_HEIGHT, 2)
        playhead_palette = Palette(2)
        playhead_palette[0] = 0x657c95  # Transparent
        playhead_palette[1] = 0xFF0000  # Red playhead line

        for y in range(self.STAFF_HEIGHT):
            playhead_bitmap[0, y] = 1
            playhead_bitmap[1, y] = 1

        self.playhead = TileGrid(
            playhead_bitmap,
            pixel_shader=playhead_palette,
            x=0,
            y=self.STAFF_Y_START
        )
        self.playhead.x = -10  # Start off-screen

        return self.playhead

    def create_highlight(self):
        """Create a highlight marker for the closest valid note position"""
        highlight_bitmap = Bitmap(self.SCREEN_WIDTH, 3, 2)
        highlight_palette = Palette(2)
        highlight_palette[0] = 0x657c95  # Transparent
        highlight_palette[1] = 0x007700  # Highlight color (green)

        for x in range(self.SCREEN_WIDTH):
            highlight_bitmap[x, 1] = 1

        self.highlight_grid = TileGrid(highlight_bitmap, pixel_shader=highlight_palette)
        self.highlight_grid.y = self.note_manager.note_positions[0]  # Start at first position

        return self.highlight_grid
