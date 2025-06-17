# SPDX-FileCopyrightText: 2025 John Park and Claude AI for Adafruit Industries
#
# SPDX-License-Identifier: MIT
"""
# control_panel.py: CircuitPython Music Staff Application component
"""

# pylint: disable=import-error
from displayio import Group, Bitmap, Palette, TileGrid
from adafruit_display_text.bitmap_label import Label
import terminalio


# pylint: disable=invalid-name,no-member,too-many-instance-attributes,too-many-arguments
# pylint: disable=too-many-branches,too-many-statements, trailing-whitespace
class ControlPanel:
    """Manages transport controls and channel selectors"""

    def __init__(self, screen_width, screen_height):
        self.SCREEN_WIDTH = screen_width
        self.SCREEN_HEIGHT = screen_height

        # Button dimensions
        self.BUTTON_WIDTH = 64  # Updated for bitmap buttons
        self.BUTTON_HEIGHT = 48  # Updated for bitmap buttons
        self.BUTTON_SPACING = 10

        # Channel button dimensions
        self.CHANNEL_BUTTON_SIZE = 20
        self.CHANNEL_BUTTON_SPACING = 5
        self.CHANNEL_BUTTON_Y = 5

        # Transport area
        self.TRANSPORT_AREA_Y = (int(screen_height * 0.1) +
                                int((screen_height - int(screen_height * 0.1) -
                                    int(screen_height * 0.2)) * 0.95) + 10)

        # State
        self.is_playing = False
        self.loop_enabled = False

        # Channel colors (reduced from 8 to 6)
        self.CHANNEL_COLORS = [
            0x000000,  # Channel 1: Black (default)
            0xFF0000,  # Channel 2: Red
            0x00FF00,  # Channel 3: Green
            0x0000FF,  # Channel 4: Blue
            0xFF00FF,  # Channel 5: Magenta
            0xFFAA00,  # Channel 6: Orange
        ]
        self.current_channel = 0

        # UI elements
        self.play_button = None
        self.stop_button = None
        self.loop_button = None
        self.clear_button = None
        self.play_button_bitmap = None
        self.stop_button_bitmap = None
        self.loop_button_bitmap = None
        self.clear_button_bitmap = None
        self.channel_selector = None

        # For bitmap buttons
        self.button_sprites = None

        # Center points for fallback play/loop buttons
        self.play_center_x = self.BUTTON_WIDTH // 2
        self.play_center_y = self.BUTTON_HEIGHT // 2
        self.play_size = 10
        self.loop_center_x = self.BUTTON_WIDTH // 2
        self.loop_center_y = self.BUTTON_HEIGHT // 2
        self.loop_radius = 6

    def create_channel_buttons(self):
        """Create channel selector buttons at the top of the screen using sprites"""
        channel_group = Group()

        # Add a highlight indicator for the selected channel (yellow outline only)
        # Create bitmap for channel selector with appropriate dimensions
        btn_size = self.CHANNEL_BUTTON_SIZE
        channel_select_bitmap = Bitmap(btn_size + 6, btn_size + 6, 2)
        channel_select_palette = Palette(2)
        channel_select_palette[0] = 0x444444  # Same as background color (dark gray)
        channel_select_palette[1] = 0xFFFF00  # Yellow highlight
        channel_select_palette.make_transparent(0)  # Make background transparent

        # Draw just the outline (no filled background)
        bitmap_size = btn_size + 6
        for x in range(bitmap_size):
            for y in range(bitmap_size):
                # Draw only the border pixels
                if (x == 0 or x == bitmap_size - 1 or
                    y == 0 or y == bitmap_size - 1):
                    channel_select_bitmap[x, y] = 1  # Yellow outline
                else:
                    channel_select_bitmap[x, y] = 0  # Transparent background

        self.channel_selector = TileGrid(
            channel_select_bitmap,
            pixel_shader=channel_select_palette,
            x=7,
            y=self.CHANNEL_BUTTON_Y - 3
        )
        channel_group.append(self.channel_selector)

        return channel_group, self.channel_selector

    def create_transport_controls(self, sprite_manager):
        """Create transport controls using bitmap buttons"""
        transport_group = Group()

        # Check if button sprites were successfully loaded
        if (sprite_manager.play_up is None or sprite_manager.stop_up is None or
            sprite_manager.loop_up is None or sprite_manager.clear_up is None):
            print("Warning: Button sprites not loaded, using fallback buttons")
            return self._create_fallback_transport_controls()

        # Button spacing based on the new size (64x48)
        button_spacing = 10
        button_y = self.SCREEN_HEIGHT - 50  # Allow some margin at bottom

        # Create TileGrids for each button using the "up" state initially
        self.stop_button = TileGrid(
            sprite_manager.stop_up,
            pixel_shader=sprite_manager.stop_up_palette,
            x=10,
            y=button_y
        )

        self.play_button = TileGrid(
            sprite_manager.play_up,
            pixel_shader=sprite_manager.play_up_palette,
            x=10 + 64 + button_spacing,
            y=button_y
        )

        self.loop_button = TileGrid(
            sprite_manager.loop_up,
            pixel_shader=sprite_manager.loop_up_palette,
            x=10 + 2 * (64 + button_spacing),
            y=button_y
        )

        self.clear_button = TileGrid(
            sprite_manager.clear_up,
            pixel_shader=sprite_manager.clear_up_palette,
            x=10 + 3 * (64 + button_spacing),
            y=button_y
        )

        # Store references to the button bitmaps and palettes
        self.button_sprites = {
            'play': {
                'up': (sprite_manager.play_up, sprite_manager.play_up_palette),
                'down': (sprite_manager.play_down, sprite_manager.play_down_palette)
            },
            'stop': {
                'up': (sprite_manager.stop_up, sprite_manager.stop_up_palette),
                'down': (sprite_manager.stop_down, sprite_manager.stop_down_palette)
            },
            'loop': {
                'up': (sprite_manager.loop_up, sprite_manager.loop_up_palette),
                'down': (sprite_manager.loop_down, sprite_manager.loop_down_palette)
            },
            'clear': {
                'up': (sprite_manager.clear_up, sprite_manager.clear_up_palette),
                'down': (sprite_manager.clear_down, sprite_manager.clear_down_palette)
            }
        }

        # Save the button dimensions
        self.BUTTON_WIDTH = 64
        self.BUTTON_HEIGHT = 48

        # Add buttons to the group
        transport_group.append(self.stop_button)
        transport_group.append(self.play_button)
        transport_group.append(self.loop_button)
        transport_group.append(self.clear_button)

        return (transport_group, self.play_button, self.stop_button,
                self.loop_button, self.clear_button)

    # pylint: disable=too-many-locals
    def _create_fallback_transport_controls(self):
        """Create fallback transport controls using drawn buttons (original implementation)"""
        transport_group = Group()

        # Create button bitmaps
        self.play_button_bitmap = Bitmap(self.BUTTON_WIDTH, self.BUTTON_HEIGHT, 3)
        self.stop_button_bitmap = Bitmap(self.BUTTON_WIDTH, self.BUTTON_HEIGHT, 3)
        self.loop_button_bitmap = Bitmap(self.BUTTON_WIDTH, self.BUTTON_HEIGHT, 3)
        self.clear_button_bitmap = Bitmap(self.BUTTON_WIDTH, self.BUTTON_HEIGHT, 3)

        # Button palettes with custom colors
        play_button_palette = Palette(3)
        play_button_palette[0] = 0x444444  # Dark gray background
        play_button_palette[1] = 0x000000  # Black text/border
        play_button_palette[2] = 0xFFD700  # Golden yellow for active state

        stop_button_palette = Palette(3)
        stop_button_palette[0] = 0x444444  # Dark gray background
        stop_button_palette[1] = 0x000000  # Black text/border
        stop_button_palette[2] = 0xFF00FF  # Magenta for active state

        loop_button_palette = Palette(3)
        loop_button_palette[0] = 0x444444  # Dark gray background
        loop_button_palette[1] = 0x000000  # Black text/border
        loop_button_palette[2] = 0xFFD700  # Golden yellow for active state

        clear_button_palette = Palette(3)
        clear_button_palette[0] = 0x444444  # Dark gray background
        clear_button_palette[1] = 0x000000  # Black text/border
        clear_button_palette[2] = 0xFF0000  # Red for pressed state

        # Create Stop button
        for x in range(self.BUTTON_WIDTH):
            for y in range(self.BUTTON_HEIGHT):
                # Draw border
                if (x == 0 or x == self.BUTTON_WIDTH - 1 or
                    y == 0 or y == self.BUTTON_HEIGHT - 1):
                    self.stop_button_bitmap[x, y] = 1
                # Fill with magenta (active state)
                else:
                    self.stop_button_bitmap[x, y] = 2

        # Create Play button
        for x in range(self.BUTTON_WIDTH):
            for y in range(self.BUTTON_HEIGHT):
                # Draw border
                if (x == 0 or x == self.BUTTON_WIDTH - 1 or
                    y == 0 or y == self.BUTTON_HEIGHT - 1):
                    self.play_button_bitmap[x, y] = 1
                # Fill with gray (inactive state)
                else:
                    self.play_button_bitmap[x, y] = 0

        # Draw play symbol (triangle)
        for y in range(
            self.play_center_y - self.play_size//2,
            self.play_center_y + self.play_size//2
        ):
            width = (y - (self.play_center_y - self.play_size//2)) // 2
            for x in range(
                self.play_center_x - self.play_size//4,
                self.play_center_x - self.play_size//4 + width
            ):
                if 0 <= x < self.BUTTON_WIDTH and 0 <= y < self.BUTTON_HEIGHT:
                    self.play_button_bitmap[x, y] = 1

        # Create Loop button
        for x in range(self.BUTTON_WIDTH):
            for y in range(self.BUTTON_HEIGHT):
                # Draw border
                if (x == 0 or x == self.BUTTON_WIDTH - 1 or
                    y == 0 or y == self.BUTTON_HEIGHT - 1):
                    self.loop_button_bitmap[x, y] = 1
                # Fill with gray (inactive state)
                else:
                    self.loop_button_bitmap[x, y] = 0

        # Draw loop symbol (circle with arrow)
        for x in range(self.BUTTON_WIDTH):
            for y in range(self.BUTTON_HEIGHT):
                dx = x - self.loop_center_x
                dy = y - self.loop_center_y
                # Draw circle outline
                if self.loop_radius - 1 <= (dx*dx + dy*dy)**0.5 <= self.loop_radius + 1:
                    if 0 <= x < self.BUTTON_WIDTH and 0 <= y < self.BUTTON_HEIGHT:
                        self.loop_button_bitmap[x, y] = 1

        # Add arrow to loop symbol
        for i in range(4):
            x = self.loop_center_x + int(self.loop_radius * 0.7) - i
            y = self.loop_center_y - self.loop_radius - 1 + i
            if 0 <= x < self.BUTTON_WIDTH and 0 <= y < self.BUTTON_HEIGHT:
                self.loop_button_bitmap[x, y] = 1

            x = self.loop_center_x + int(self.loop_radius * 0.7) - i
            y = self.loop_center_y - self.loop_radius - 1 - i + 2
            if 0 <= x < self.BUTTON_WIDTH and 0 <= y < self.BUTTON_HEIGHT:
                self.loop_button_bitmap[x, y] = 1

        # Create Clear button
        for x in range(self.BUTTON_WIDTH):
            for y in range(self.BUTTON_HEIGHT):
                # Draw border
                if (x == 0 or x == self.BUTTON_WIDTH - 1 or
                    y == 0 or y == self.BUTTON_HEIGHT - 1):
                    self.clear_button_bitmap[x, y] = 1
                # Fill with gray background
                else:
                    self.clear_button_bitmap[x, y] = 0

        # Create button TileGrids
        x_offset = 10
        y_pos = self.SCREEN_HEIGHT - 40

        self.stop_button = TileGrid(
            self.stop_button_bitmap,
            pixel_shader=stop_button_palette,
            x=x_offset,
            y=y_pos
        )

        x_offset += self.BUTTON_WIDTH + self.BUTTON_SPACING
        self.play_button = TileGrid(
            self.play_button_bitmap,
            pixel_shader=play_button_palette,
            x=x_offset,
            y=y_pos
        )

        x_offset += self.BUTTON_WIDTH + self.BUTTON_SPACING
        self.loop_button = TileGrid(
            self.loop_button_bitmap,
            pixel_shader=loop_button_palette,
            x=x_offset,
            y=y_pos
        )

        x_offset += self.BUTTON_WIDTH + self.BUTTON_SPACING
        self.clear_button = TileGrid(
            self.clear_button_bitmap,
            pixel_shader=clear_button_palette,
            x=x_offset,
            y=y_pos
        )

        # Add buttons to group
        transport_group.append(self.stop_button)
        transport_group.append(self.play_button)
        transport_group.append(self.loop_button)
        transport_group.append(self.clear_button)

        # Add "CLEAR" text to clear button
        text_color = 0x000000  # Black text
        label_x = self.clear_button.x + self.BUTTON_WIDTH // 2
        label_y = self.clear_button.y + self.BUTTON_HEIGHT // 2

        clear_label = Label(
            terminalio.FONT,
            text="CLEAR",
            color=text_color,
            scale=1
        )
        clear_label.anchor_point = (0.5, 0.5)  # Center the text
        clear_label.anchored_position = (label_x, label_y)
        transport_group.append(clear_label)

        return (transport_group, self.play_button, self.stop_button,
                self.loop_button, self.clear_button)
