# SPDX-FileCopyrightText: 2025 John Park and Claude AI for Adafruit Industries
#
# SPDX-License-Identifier: MIT
"""
Sprite manager for CircuitPython Music Staff Application.
Handles loading and managing sprite images and palettes.
"""

# pylint: disable=import-error, trailing-whitespace
import adafruit_imageload
from displayio import Palette, TileGrid


# pylint: disable=too-many-instance-attributes,invalid-name,broad-except
class SpriteManager:
    """Manages sprites and palettes for note display"""

    def __init__(self, bg_color=0x8AAD8A):
        """Initialize the sprite manager"""
        self.bg_color = bg_color

        # Initialize palettes as empty lists first
        self.note_palettes = []
        self.preview_palettes = []

        # Sprites
        self.mario_head = None
        self.mario_palette = None
        self.heart_note = None
        self.heart_palette = None
        self.drum_note = None
        self.drum_palette = None
        # Add new sprite variables
        self.meatball_note = None
        self.meatball_palette = None
        self.star_note = None
        self.star_palette = None
        self.bot_note = None
        self.bot_palette = None

        # Channel colors (still need these for palette management)
        self.channel_colors = [
            0x000000,  # Channel 1: Black (default)
            0xFF0000,  # Channel 2: Red
            0x00FF00,  # Channel 3: Green
            0x0000FF,  # Channel 4: Blue
            0xFF00FF,  # Channel 5: Magenta
            0xFFAA00,  # Channel 6: Orange
        ]

        # Add button sprites
        self.play_up = None
        self.play_up_palette = None
        self.play_down = None
        self.play_down_palette = None
        self.stop_up = None
        self.stop_up_palette = None
        self.stop_down = None
        self.stop_down_palette = None
        self.loop_up = None
        self.loop_up_palette = None
        self.loop_down = None
        self.loop_down_palette = None
        self.clear_up = None
        self.clear_up_palette = None
        self.clear_down = None
        self.clear_down_palette = None

        # Load sprites
        self.load_sprites()

        # Load button sprites
        self.load_button_sprites()

        # Create palettes
        self.create_palettes()

    def load_sprites(self):
        """Load sprite images"""
        try:
            # Load the Lars note bitmap for channel 1 notes
            self.mario_head, self.mario_palette = adafruit_imageload.load(
                "/sprites/lars_note.bmp"
            )
            # Make the background color transparent (not just the same color)
            self.mario_palette.make_transparent(0)

            # Load the Heart note bitmap for channel 2 notes
            self.heart_note, self.heart_palette = adafruit_imageload.load(
                "/sprites/heart_note.bmp"
            )
            # Make the background color transparent
            self.heart_palette.make_transparent(0)

            # Load the Drum note bitmap for channel 3 notes
            self.drum_note, self.drum_palette = adafruit_imageload.load(
                "/sprites/drum_note.bmp"
            )
            # Make the background color transparent
            self.drum_palette.make_transparent(0)

            # Load the new sprites for channels 4, 5, and 6
            # Meatball for channel 4
            self.meatball_note, self.meatball_palette = adafruit_imageload.load(
                "/sprites/meatball.bmp"
            )
            self.meatball_palette.make_transparent(0)

            # Star for channel 5
            self.star_note, self.star_palette = adafruit_imageload.load(
                "/sprites/star.bmp"
            )
            self.star_palette.make_transparent(0)

            # Bot for channel 6
            self.bot_note, self.bot_palette = adafruit_imageload.load("/sprites/bot.bmp")
            self.bot_palette.make_transparent(0)

        except Exception as e:
            print(f"Error loading sprites: {e}")

    def create_palettes(self):
        """Create palettes for notes and preview"""
        # Create a palette for music notes with multiple colors
        for channel_color in self.channel_colors:
            palette = Palette(2)
            palette[0] = self.bg_color  # Transparent (sage green background)
            palette[1] = channel_color  # Note color for this channel
            self.note_palettes.append(palette)

        # Create a preview palette with multiple colors
        for channel_color in self.channel_colors:
            palette = Palette(2)
            palette[0] = self.bg_color  # Transparent (sage green background)
            # For preview, use a lighter version of the channel color
            r = ((channel_color >> 16) & 0xFF) // 2 + 0x40
            g = ((channel_color >> 8) & 0xFF) // 2 + 0x40
            b = (channel_color & 0xFF) // 2 + 0x40
            preview_color = (r << 16) | (g << 8) | b
            palette[1] = preview_color
            self.preview_palettes.append(palette)

    def create_preview_note(self, current_channel, note_bitmap):
        """Create preview note based on channel"""
        if current_channel == 0:  # Channel 1 uses Lars note
            preview_tg = TileGrid(self.mario_head, pixel_shader=self.mario_palette)
        elif current_channel == 1:  # Channel 2 uses Heart note
            preview_tg = TileGrid(self.heart_note, pixel_shader=self.heart_palette)
        elif current_channel == 2:  # Channel 3 uses Drum note
            preview_tg = TileGrid(self.drum_note, pixel_shader=self.drum_palette)
        elif current_channel == 3:  # Channel 4 uses Meatball
            preview_tg = TileGrid(self.meatball_note, pixel_shader=self.meatball_palette)
        elif current_channel == 4:  # Channel 5 uses Star
            preview_tg = TileGrid(self.star_note, pixel_shader=self.star_palette)
        elif current_channel == 5:  # Channel 6 uses Bot
            preview_tg = TileGrid(self.bot_note, pixel_shader=self.bot_palette)
        else:  # Fallback to colored circle
            preview_tg = TileGrid(
                note_bitmap,
                pixel_shader=self.preview_palettes[current_channel]
            )

        preview_tg.x = 0
        preview_tg.y = 0
        preview_tg.hidden = True  # Start with preview hidden

        return preview_tg

    def load_button_sprites(self):
        """Load button sprites for transport controls"""
        try:
            # Load play button images
            self.play_up, self.play_up_palette = adafruit_imageload.load(
                "/sprites/play_up.bmp"
            )
            self.play_up_palette.make_transparent(0)

            self.play_down, self.play_down_palette = adafruit_imageload.load(
                "/sprites/play_down.bmp"
            )
            self.play_down_palette.make_transparent(0)

            # Load stop button images
            self.stop_up, self.stop_up_palette = adafruit_imageload.load(
                "/sprites/stop_up.bmp"
            )
            self.stop_up_palette.make_transparent(0)

            self.stop_down, self.stop_down_palette = adafruit_imageload.load(
                "/sprites/stop_down.bmp"
            )
            self.stop_down_palette.make_transparent(0)

            # Load loop button images
            self.loop_up, self.loop_up_palette = adafruit_imageload.load(
                "/sprites/loop_up.bmp"
            )
            self.loop_up_palette.make_transparent(0)

            self.loop_down, self.loop_down_palette = adafruit_imageload.load(
                "/sprites/loop_down.bmp"
            )
            self.loop_down_palette.make_transparent(0)

            # Load clear button images
            self.clear_up, self.clear_up_palette = adafruit_imageload.load(
                "/sprites/clear_up.bmp"
            )
            self.clear_up_palette.make_transparent(0)

            self.clear_down, self.clear_down_palette = adafruit_imageload.load(
                "/sprites/clear_down.bmp"
            )
            self.clear_down_palette.make_transparent(0)

            return True
        except Exception as e:
            print(f"Error loading button sprites: {e}")
            return False
