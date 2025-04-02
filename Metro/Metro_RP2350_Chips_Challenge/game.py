# SPDX-FileCopyrightText: 2025 Melissa LeBlanc-Williams
#
# SPDX-License-Identifier: MIT

from random import randint, random
from time import sleep
import sys
import math
import bitmaptools
import adafruit_imageload
import displayio
from databuffer import DataBuffer
from gamelogic import GameLogic
from point import Point
from definitions import victory_messages, winning_message, final_levels
from definitions import GM_NEWGAME, GM_NORMAL, GM_PAUSED, GM_LEVELWON, GM_CHIPDEAD, GM_GAMEWON
from definitions import GAMEPLAY_COMMANDS, MESSAGE_COMMANDS, PASSWORD_COMMANDS
from definitions import NONE, QUIT, NEXT_LEVEL, PREVIOUS_LEVEL, RESTART_LEVEL, GOTO_LEVEL
from definitions import PAUSE, OK, CANCEL, CHANGE_FIELDS, DELCHAR, SF_SHOWHINT
from definitions import TYPE_EMPTY, TYPE_EXIT, TYPE_EXITED_CHIP, TYPE_CHIP
from definitions import TYPE_EXIT_EXTRA_1, TYPE_EXIT_EXTRA_2, DOWN, TICKS_PER_SECOND
from keyboard import KeyboardBuffer
from adafruit_bitmap_font import bitmap_font
from dialog import Dialog, InputFields
from savestate import SaveState
from microcontroller import nvm

# Colors must be colors in palette
LARGE_FONT = bitmap_font.load_font("/fonts/Arial-Bold-10.pcf")
SMALL_FONT = bitmap_font.load_font("/fonts/Arial-8.pcf")

colors = {
    "key_color": 0xAAFF00, # Light Green
    "title_text_color": 0xFFFF00, # Yellow
    "hint_text_color": 0x00FFFF, # Cyan
    "default_dialog_text_color": 0x000000, # Black
    "paused_text_color": 0xFF0000, # Red
    "dialog_background": 0xFFFFFF, # Black
    "bounding_box_light": 0xFFFFFF, # White
    "bounding_box_dark": 0x808080, # Dark Gray
    "tile_bg_color": 0xAABFAA, # Light Gray
    "light_gray": 0xAABFAA, # Light Gray
    "dark_gray": 0x808080, # Dark Gray
    "black": 0x000000, # Black
    "white": 0xFFFFFF, # White
    "purple": 0xAA00ff # Purple
}

# Image Files
SPRITESHEET_FILE = "bitmaps/spritesheet_24_keyed.bmp"
BACKGROUND_FILE = "bitmaps/background.bmp"
INFO_FILE = "bitmaps/info.bmp"
DIGITS_FILE = "bitmaps/digits.bmp"
CHIPEND_FILE = "bitmaps/chipend.bmp"

# Layout Offsets
VIEWPORT_OFFSET = (1, 10)
INFO_OFFSET = (219, 10)
LEVEL_DIGITS_OFFSET = (INFO_OFFSET[0] + 26, INFO_OFFSET[1] + 23)
TIME_DIGITS_OFFSET = (INFO_OFFSET[0] + 26, INFO_OFFSET[1] + 69)
CHIPS_DIGITS_OFFSET = (INFO_OFFSET[0] + 26, INFO_OFFSET[1] + 123)
ITEMS_OFFSET = (INFO_OFFSET[0] + 2, INFO_OFFSET[1] + 153)
HINT_OFFSET = (INFO_OFFSET[0], INFO_OFFSET[1] + 96)

def get_victory_message(deaths):
    # go through victory message in reverse order
    for i in range(5, -1, -1):
        if deaths >= i:
            return victory_messages.get(i, "Something went wrong!")
    return None

class Game:
    def __init__(self, display, data_file, **kwargs):
        self._display = display
        self._images = {}
        self._buffers = {}
        self._message_group = displayio.Group()
        self._loading_group = displayio.Group()
        self._tile_size = 24  # Default tile size (length and width)
        self._digit_dims = (0, 0)
        self._gamelogic = GameLogic(data_file, **kwargs)
        self._databuffer = DataBuffer()
        self._color_index = {}
        self._init_display()
        self._databuffer.set_data_structure({
            "info_drawn": False,
            "title_visible": False,
            "level": -1,
            "time_left": 0,
            "chips_needed": -1,
            "keys": [False, False, False, False],
            "boots": [False, False, False, False],
            "viewport_tiles_top": [[-1]*9 for _ in range(9)],
            "viewport_tiles_bottom": [[-1]*9 for _ in range(9)],
            "hint_visible": False,
            "pause_visible": False,
            "message_shown": False,
        })
        self.dialog = Dialog(self._color_index, self._shader)
        self._input_fields = InputFields()
        self._show_loading()
        self._savestate = SaveState()
        self._current_command_set = GAMEPLAY_COMMANDS
        self._keyboard = KeyboardBuffer(self._current_command_set.keys())
        self._deaths = 0
        self._pw_request_level = None

    def _init_display(self):
        # Set up the Shader and Color Index
        self._shader = self._load_images()
        self.extract_color_indices()
        self._shader.make_transparent(self._color_index["key_color"])

        # Create the Buffers and add key color for transparency
        buffer_group = displayio.Group()
        self._buffers["main"] = displayio.Bitmap(self._display.width, self._display.height, 256)
        self._buffers["main"].fill(self._color_index["key_color"])
        self._buffers["loading"] = displayio.Bitmap(self._display.width, self._display.height, 256)
        self._buffers["loading"].fill(self._color_index["key_color"])

        buffer_group.append(
            displayio.TileGrid(
                self._images["background"],
                pixel_shader=self._shader,
                width=2,
                height=2,
            )
        )
        buffer_group.append(
            displayio.TileGrid(
                self._buffers["main"],
                pixel_shader=self._shader,
            )
        )
        buffer_group.append(self._message_group)
        buffer_group.append(self._loading_group)

        self._display.root_group = buffer_group

    def _load_images(self):
        self._images["spritesheet"], shader = adafruit_imageload.load(SPRITESHEET_FILE)
        self._images["background"], _ = adafruit_imageload.load(BACKGROUND_FILE)
        self._tile_size = self._images["spritesheet"].height // 16
        self._images["info"], _ = adafruit_imageload.load(INFO_FILE)
        self._images["digits"], _ = adafruit_imageload.load(DIGITS_FILE)
        self._images["chipend"], _ = adafruit_imageload.load(CHIPEND_FILE)
        self._digit_dims = (self._images["digits"].width, self._images["digits"].height // 24)
        return shader

    def extract_color_indices(self):
        for key, color in colors.items():
            self._color_index[key] = self.get_color_index(color)

    def get_color_index(self, color, shader=None):
        if shader is None:
            shader = self._shader
        for index, palette_color in enumerate(shader):
            if palette_color == color:
                return index
        return None

    def reset_level(self, reset_deaths=True):
        self._show_loading()
        if reset_deaths:
            self._deaths = 0
        self._gamelogic.reset()
        self._remove_all_message_layers()
        self._databuffer.reset((
            "viewport_tiles_top",
            "level",
            "time_left",
            "chips_needed",
            "keys",
            "boots",
            "viewport_tiles_top",
            "title_visible",
            "message_shown",
            "pause_visible",
        ))
        self._databuffer.reset()
        self._keyboard.clear()
        self._pw_request_level = None

    def change_input_commands(self, commands):
        previous_commands = self._current_command_set
        self._current_command_set = commands
        self._keyboard.set_valid_sequences(commands.keys())
        return previous_commands

    def input(self):
        key = self._keyboard.get_key()
        if key:
            return self._current_command_set[key]
        return NONE

    def wait_for_valid_input(self):
        # Wait for a valid input (useful for dialogs)
        while True:
            key = self._keyboard.get_key()
            if key:
                return self._current_command_set[key]

    def save_level(self):
        self._savestate.add_level_password(
            self._gamelogic.current_level_number,
            self._gamelogic.current_level.password
        )

    def tick(self):
        """
        This is the main game function. It will be responsible for handling game states
        and handling keyboard input.
        """
        game_mode = self._gamelogic.get_game_mode()
        if game_mode == GM_NEWGAME:
            self._draw_frame()
            self.reset_level()
            level = nvm[0]
            level_password = self._gamelogic.current_level.password
            save_password = ""
            for byte, _ in enumerate(level_password):
                save_password += chr(nvm[1 + byte])
            if level_password != save_password:
                level = 1
            self._gamelogic.set_level(level)
            self.save_level()

        command = self._handle_commands()

        # Handle Game Modes
        if game_mode == GM_NORMAL:
            if command == PAUSE:
                self._gamelogic.set_game_mode(GM_PAUSED)
                self._draw_pause_screen()
            self._gamelogic.advance_game(command)
        elif game_mode == GM_CHIPDEAD:
            self.show_message(self._gamelogic.get_death_message())
            self.reset_level(False)
            self._gamelogic.set_level(self._gamelogic.current_level_number)
        elif game_mode == GM_PAUSED:
            if command == PAUSE:
                self._draw_pause_screen(False)
                self._gamelogic.revert_game_mode()
        elif game_mode == GM_LEVELWON:
            self.handle_win()

        # Draw every other tick to increase responsiveness
        if not self._gamelogic.get_tick() or self._gamelogic.get_tick() & 1:
            self._draw_frame()

    def _handle_commands(self):
        command = self.input()
        self._keyboard.clear()
        # Handle Commands
        if command == QUIT:
            sys.exit()
        elif command == NEXT_LEVEL:
            if self._gamelogic.current_level_number < self._gamelogic.last_level:
                if self._savestate.is_level_unlocked(self._gamelogic.current_level_number + 1):
                    self.reset_level()
                    self._gamelogic.inc_level()
                    self.save_level()
                else:
                    self._input_fields.clear()
                    self._input_fields.add("Password", InputFields.ALPHANUMERIC)
                    self._databuffer.dataset["message_shown"] = False
                    self._pw_request_level = self._gamelogic.current_level_number + 1
                    self.request_password()
        elif command == PREVIOUS_LEVEL:
            if self._gamelogic.current_level_number > 1:
                if self._savestate.is_level_unlocked(self._gamelogic.current_level_number - 1):
                    self.reset_level()
                    self._gamelogic.dec_level()
                    self.save_level()
                else:
                    # If not, load the password dialog
                    self._input_fields.clear()
                    self._input_fields.add("Password", InputFields.ALPHANUMERIC)
                    self._databuffer.dataset["message_shown"] = False
                    self._pw_request_level = self._gamelogic.current_level_number - 1
                    self.request_password()
        elif command == RESTART_LEVEL:
            self.reset_level()
            self._gamelogic.set_level(self._gamelogic.current_level_number)
        elif command == GOTO_LEVEL:
            # We need to establish fields to keep track of where we are typing and the values
            self._input_fields.clear()
            self._input_fields.add("Level number", InputFields.NUMERIC, 0)
            self._input_fields.add("Password", InputFields.ALPHANUMERIC)
            self.request_password()
        return command

    def show_score_tally(self):
        time_left = (self._gamelogic.current_level.time_limit -
                     math.ceil(self._gamelogic.get_tick() / TICKS_PER_SECOND))
        time_left = max(time_left, 0)
        level = self._gamelogic.current_level_number
        score = self._savestate.calculate_score(level, time_left, self._deaths)
        previous_score = self._savestate.level_score(self._gamelogic.current_level_number)
        best_score = self._savestate.set_level_score(level, score[2], time_left)
        score_message = ""
        if previous_score[0] == 0:
            score_message = "\n\nYou have established a time record for this level!"
        elif best_score[1] < previous_score[1]:
            difference = previous_score[1] - best_score[1]
            score_message = (
                f"\n\nYou beat the previous time record by {difference} seconds!"
            )
        elif best_score[0] > previous_score[0]:
            difference = best_score[0] - previous_score[0]
            score_message = (
                f"\n\nYou increased your score on this level by {difference} points!"
            )
        # Update the score (with new total score)
        score = self._savestate.calculate_score(level, time_left, self._deaths)

        message = f"""Level {self._gamelogic.current_level_number} Complete!
{get_victory_message(self._deaths)}

Time Bonus: {score[0]}
Level Bonus: {score[1]}
Level Score: {score[2]}
Total Score: {score[3]}"""
        message += score_message
        self.show_message(message, button_text="Onward")

    def handle_win(self):
        self._draw_frame()
        # Show the level score tally
        self.show_score_tally()

        # Check if we are at the last level and set game mode appropriately
        level_check = self._gamelogic.current_level_number
        if self._gamelogic.current_level_number == self._gamelogic.last_level:
            level_check = -1
        if level_check in final_levels:
            self._show_winning_sequence()

        # check for decade message
        decade_message = self._gamelogic.get_decade_message()
        if decade_message:
            self.show_message(decade_message)

        if self._gamelogic.get_game_mode() == GM_GAMEWON:
            # Show winning message
            self.show_message(winning_message.format(
                completed_levels=self._savestate.total_completed_levels,
                total_score=self._savestate.total_score,
            ), width=200)
            self.change_input_commands(GAMEPLAY_COMMANDS)
        else:
            # Go to the next level
            self.reset_level()
            self._gamelogic.inc_level()
            self.save_level()

    def show_message(self, message, *, button_text="OK", width=150):
        buffer = self._add_message_layer()
        self.dialog.display_message(
            message,
            SMALL_FONT,
            width,
            None,
            None,
            None,
            buffer,
            center_dialog_horizontally=True,
            center_dialog_vertically=True,
            button_text=button_text,
        )
        current_commands = self.change_input_commands(MESSAGE_COMMANDS)
        # Await input
        self.wait_for_valid_input()
        # Clear message
        self._remove_message_layer()
        # Set input commands to previous
        self.change_input_commands(current_commands)
        # Maybe remove item from sequence later

    def request_password(self):
        #pylint: disable=too-many-branches
        current_commands = self.change_input_commands(PASSWORD_COMMANDS)
        self._draw_pause_screen()
        while True:
            command = NONE
            while command not in (OK, CANCEL):
                self._draw_password_dialog()
                command = self.wait_for_valid_input()
                if command == CHANGE_FIELDS:
                    self._input_fields.next_field()
                elif command == DELCHAR:
                    self._input_fields.active_field_value = (
                        self._input_fields.active_field_value[:-1]
                    )
                elif isinstance(command, str):
                    command = command.upper()
                    active_field = self._input_fields.active_field
                    if (active_field["max_length"] is None or
                        0 <= len(active_field["value"]) < active_field["max_length"]):
                        if active_field["type"] == InputFields.NUMERIC and command.isdigit():
                            self._input_fields.active_field_value += command
                        elif active_field["type"] == InputFields.ALPHA and command.isalpha():
                            self._input_fields.active_field_value += command
                        elif active_field["type"] == InputFields.ALPHANUMERIC:
                            self._input_fields.active_field_value += command
            if command == OK:
                level = self._input_fields.get_value("level_number")
                if level is None and self._pw_request_level is not None:
                    level = self._pw_request_level
                password = self._input_fields.get_value("password")
                if level == 0 and self._savestate.find_unlocked_level(password) is not None:
                    level = self._savestate.find_unlocked_level(password)
                if not 0 < level <= self._gamelogic.last_level:
                    self.show_message("That is not a valid level number.")
                elif (level and password and
                      self._gamelogic.current_level.passwords[level] != password):
                    self.show_message("You must enter a valid password.")
                elif (self._savestate.is_level_unlocked(level) and
                    self._savestate.find_unlocked_level(level) is None
                    and self._savestate.find_unlocked_level(password) is None):
                    self.show_message("You must enter a valid password.")
                else:
                    self._remove_all_message_layers()
                    self.change_input_commands(current_commands)
                    self.reset_level()
                    self._gamelogic.set_level(level)
                    self.save_level()
                    return
            elif command == CANCEL:
                self._remove_all_message_layers()
                self.change_input_commands(current_commands)
                return

    def _draw_number(self, value, offset, yellow_condition = None):
        yellow = False
        if yellow_condition is not None:
            yellow = yellow_condition(value)

        buffer = self._buffers["main"]

        if value < 0:
            # All digits are hyphens
            for slot in range(3):
                bitmaptools.blit(
                    buffer,
                    self._images["digits"],
                    offset[0] + slot * self._digit_dims[0],
                    offset[1],
                    0,
                    0, self._digit_dims[0],
                    self._digit_dims[1]
                )
            return

        color_offset = 0 if yellow else self._digit_dims[1] * 12

        calc_value = value
        for slot in range(3):
            if (value < 100 and slot == 0) or (value < 10 and slot == 1):
                tile_offset = self._digit_dims[1] # a space
            else:
                tile_offset = (11 - (calc_value // (10 ** (2 - slot)))) * self._digit_dims[1]
                calc_value -= (calc_value // (10 ** (2 - slot)) * (10 ** (2 - slot)))
            bitmaptools.blit(
                buffer,
                self._images["digits"],
                offset[0] + slot * self._digit_dims[0],
                offset[1],
                0,
                tile_offset + color_offset, self._digit_dims[0],
                tile_offset + self._digit_dims[1] + color_offset
            )

    def _add_message_layer(self):
        # Add the message layer to the display group
        # Erase any existing stuff

        buffer = displayio.Bitmap(self._display.width, self._display.height, 256)
        buffer.fill(self._color_index["key_color"])

        self._message_group.append(
            displayio.TileGrid(
                buffer,
                pixel_shader=self._shader,
            )
        )

        return buffer

    def _remove_message_layer(self):
        # Remove the message layer from the display group
        if len(self._message_group) == 0:
            return
        self._message_group.pop()

    def _remove_all_message_layers(self):
        # Remove all message layers from the display group
        while len(self._message_group) > 0:
            self._message_group.pop()

    def _show_loading(self):
        while len(self._loading_group) > 0:
            self._loading_group.pop()
        self.dialog.display_simple(
            "Loading...",
            LARGE_FONT,
            None,
            None,
            None,
            None,
            self._buffers["loading"],
            center_dialog_horizontally=True,
            background_color_index=self._color_index["white"],
            font_color_index=self._color_index["purple"],
            padding=10,
        )
        self._loading_group.append(
            displayio.TileGrid(
                self._buffers["loading"],
                pixel_shader=self._shader,
            )
        )

    def _show_winning_sequence(self):
        #pylint: disable=too-many-locals
        self._gamelogic.set_game_mode(GM_GAMEWON)

        def get_frame_image(frame):
            # Create a tile sized bitmap
            tile_buffer = displayio.Bitmap(self._tile_size, self._tile_size, 256)
            self._draw_tile(tile_buffer, 0, 0, frame[0], frame[1])
            return tile_buffer

        # Get chips coordinates
        chip = self._gamelogic.get_chip_coords_in_viewport()
        viewport_size = self._tile_size * 9

        # Get centered screen coordinates of chip
        chip_position = Point(
            VIEWPORT_OFFSET[0] + chip.x * self._tile_size + self._tile_size // 2,
            VIEWPORT_OFFSET[1] + chip.y * self._tile_size + self._tile_size // 2
        )

        viewport_center = Point(
            VIEWPORT_OFFSET[0] + viewport_size // 2 - 1,
            VIEWPORT_OFFSET[1] + viewport_size // 2 - 1
        )

        # Chip Frames
        frames = {
            "cheering": (TYPE_EXITED_CHIP, TYPE_EMPTY),
            "standing_1": (TYPE_CHIP + DOWN, TYPE_EXIT),
            "standing_2": (TYPE_CHIP + DOWN, TYPE_EXIT_EXTRA_1),
            "standing_3": (TYPE_CHIP + DOWN, TYPE_EXIT_EXTRA_2),
        }

        # Chip Sequences
        zoom_sequence = (
            get_frame_image(frames["standing_1"]),
            get_frame_image(frames["standing_2"]),
            get_frame_image(frames["standing_3"]),
        )

        cheer_sequence = (
            get_frame_image(frames["cheering"]),
            get_frame_image(frames["standing_1"]),
        )

        viewport_upper_left = Point(
            VIEWPORT_OFFSET[0],
            VIEWPORT_OFFSET[1]
        )
        viewport_lower_right = Point(
            VIEWPORT_OFFSET[0] + viewport_size,
            VIEWPORT_OFFSET[1] + viewport_size
        )

        for i in range(32):
            source_bmp = zoom_sequence[i % len(zoom_sequence)]
            scale = 1 + ((i + 1) / 32) * 8
            scaled_tile_size = math.ceil(self._tile_size * scale)
            x = chip_position.x
            y = chip_position.y

            # Make sure the scaled tile is within the viewport
            scaled_tile_upper_left = Point(
                x - scaled_tile_size // 2,
                y - scaled_tile_size // 2
            )
            scaled_tile_lower_right = Point(
                x + scaled_tile_size // 2,
                y + scaled_tile_size // 2
            )
            if scaled_tile_upper_left.y < viewport_upper_left.y:
                y += viewport_upper_left.y - scaled_tile_upper_left.y
            elif scaled_tile_lower_right.y > viewport_lower_right.y:
                y -= scaled_tile_lower_right.y - viewport_lower_right.y
            if scaled_tile_upper_left.x < viewport_upper_left.x:
                x += viewport_upper_left.x - scaled_tile_upper_left.x
            elif scaled_tile_lower_right.x > viewport_lower_right.x:
                x -= scaled_tile_lower_right.x - viewport_lower_right.x

            bitmaptools.rotozoom(self._buffers["main"], source_bmp, ox=x, oy=y, scale=scale)
            sleep(0.1)

        for i in range(randint(16, 20)):
            source_bmp = cheer_sequence[i % len(cheer_sequence)]
            bitmaptools.rotozoom(
                self._buffers["main"],
                source_bmp,
                ox=viewport_center.x,
                oy=viewport_center.y,
                scale=9
            )
            sleep(random() * 0.5 + 0.25) # Sleep for a random time between 0.25 and 0.75 seconds

        bitmaptools.blit(
            self._buffers["main"],
            self._images["chipend"],
            VIEWPORT_OFFSET[0],
            VIEWPORT_OFFSET[1],
        )
        self.show_message("Great Job Chip! You did it! You finished the challenge!")

    def _hide_loading(self):
        while len(self._loading_group) > 0:
            self._loading_group.pop()
        self._buffers["loading"].fill(self._color_index["key_color"])

    def _draw_title_dialog(self):
        if self._gamelogic.get_game_mode() != GM_NORMAL:
            return

        data = self._databuffer.dataset
        if self._gamelogic.get_tick() > 0:
            if data["title_visible"]:
                data["title_visible"] = False
                self._remove_message_layer()
            return

        if not data["title_visible"]:
            data["title_visible"] = True
            text = (
                self._gamelogic.current_level.title +
                "\nPassword: " +
                self._gamelogic.current_level.password
            )
            buffer = self._add_message_layer()
            self.dialog.display_simple(
                text,
                LARGE_FONT,
                None,
                None,
                VIEWPORT_OFFSET[0] + 108,
                160,
                buffer,
                center_dialog_horizontally=True,
                background_color_index=self._color_index["black"],
                font_color_index=self._color_index["title_text_color"],
                padding=10,
            )
            self._hide_loading()

    def _draw_password_dialog(self):
        data = self._databuffer.dataset
        message = None
        if not data["message_shown"]:
            data["message_shown"] = True
            buttons = ("OK", "Cancel")
            if self._pw_request_level is not None:
                message = f"Enter a password\nfor level {self._pw_request_level}."
            else:
                message = "Enter a level number\n and/or password."
            buffer = self._add_message_layer()
            self.dialog.display_input(
                message,
                SMALL_FONT,
                self._input_fields.fields,
                buttons,
                200,
                None,
                None,
                None,
                buffer,
                center_dialog_horizontally=True,
                center_dialog_vertically=True,
            )

        # Update fields if needed
        for field in self._input_fields.fields:
            if field["redraw"]:
                self.dialog.draw_field(field)

    def _draw_hint(self):
        data = self._databuffer.dataset
        if not self._gamelogic.status & SF_SHOWHINT:
            if data["hint_visible"]:
                data["hint_visible"] = False
                self._remove_message_layer()
            return

        if not data["hint_visible"]:
            data["hint_visible"] = True
            buffer = self._add_message_layer()
            self.dialog.display_simple(
                "Hint: " + self._gamelogic.current_level.hint,
                SMALL_FONT,
                100,
                120,
                HINT_OFFSET[0],
                HINT_OFFSET[1],
                buffer,
                center_text_vertically=False,
                font_color_index=self._color_index["hint_text_color"],
                background_color_index=self._color_index["black"],
                padding=10,
                line_spacing=0.75,
            )

    def _draw_pause_screen(self, show=True):
        data = self._databuffer.dataset
        if show:
            if not data["pause_visible"]:
                data["pause_visible"] = True
                buffer = self._add_message_layer()
                self.dialog.display_simple(
                    "Paused",
                    LARGE_FONT,
                    216,
                    216,
                    VIEWPORT_OFFSET[0],
                    VIEWPORT_OFFSET[1],
                    buffer,
                    font_color_index=self._color_index["paused_text_color"],
                    background_color_index=self._color_index["black"],
                    padding=10,
                    line_spacing=5,
                )
            return

        if data["pause_visible"]:
            data["pause_visible"] = False
            self._remove_message_layer()

    def _draw_tile(self, buffer, x, y, top_tile, bottom_tile):
        # Create a bitmap of the tile size
        tile_size = self._tile_size
        if 0xD0 <= top_tile <= 0xD3:
            top_tile -= 0xC2

        # Bottom Layer
        if top_tile > 0x40 and bottom_tile != TYPE_EMPTY: # Bottom Tile not visible
            if 0xD0 <= bottom_tile <= 0xD3:
                bottom_tile -= 0xC2
            top_tile += 48  # Make top tile transparent
            x_src = (bottom_tile // 16) * tile_size
            y_src = (bottom_tile % 16) * tile_size
            bitmaptools.blit(
                buffer, self._images["spritesheet"], x, y, x_src, y_src,
                x_src + tile_size, y_src + tile_size
            )

        # Top Layer
        x_src = (top_tile // 16) * tile_size
        y_src = (top_tile % 16) * tile_size
        bitmaptools.blit(
            buffer, self._images["spritesheet"], x, y, x_src, y_src,
            x_src + tile_size, y_src + tile_size,
            skip_source_index=self._color_index["key_color"]
        )

    def _draw_frame(self):
        """
        This will be responsible for drawing everything to the buffer.
        """
        #pylint: disable=too-many-locals, too-many-branches
        game_mode = self._gamelogic.get_game_mode()
        buffer = self._buffers["main"]
        data = self._databuffer.dataset

        if game_mode in (GM_NORMAL, GM_LEVELWON, GM_CHIPDEAD, GM_PAUSED):
            # Draw Info Window
            if not data["info_drawn"]:
                data["info_drawn"] = True
                bitmaptools.blit(buffer, self._images["info"], INFO_OFFSET[0], INFO_OFFSET[1])

            # Draw Level Number
            if self._gamelogic.current_level_number != data["level"]:
                data["level"] = self._gamelogic.current_level_number
                self._draw_number(self._gamelogic.current_level_number, LEVEL_DIGITS_OFFSET)

            # Draw Time Left
            time_elapsed = math.ceil(self._gamelogic.get_tick() / TICKS_PER_SECOND)
            time_left = self._gamelogic.current_level.time_limit - time_elapsed
            if self._gamelogic.current_level.time_limit == 0:
                time_left = -1
            if time_left != data["time_left"]:
                data["time_left"] = time_left
                self._draw_number(
                    time_left,
                    TIME_DIGITS_OFFSET,
                    lambda x: x <= 15,
                )

            # Draw Chips Needed
            if self._gamelogic.get_chips_needed() != data["chips_needed"]:
                data["chips_needed"] = self._gamelogic.get_chips_needed()
                self._draw_number(
                    self._gamelogic.get_chips_needed(),
                    CHIPS_DIGITS_OFFSET, lambda x: x < 1
                )

            # Draw Keys Collected
            keys_images = (0x65, 0x64, 0x67, 0x66)
            for i in range(4):
                if self._gamelogic.keys[i] != data["keys"][i]:
                    data["keys"][i] = self._gamelogic.keys[i]
                    tile_id = keys_images[i] if self._gamelogic.keys[i] else TYPE_EMPTY
                    self._draw_tile(
                        buffer, ITEMS_OFFSET[0] + i * self._tile_size,
                        ITEMS_OFFSET[1], tile_id, 0
                    )

            # Draw Boots Collected
            boot_images = (0x6A, 0x6B, 0x69, 0x68)
            for i in range(4):
                if self._gamelogic.boots[i] != data["boots"][i]:
                    data["boots"][i] = self._gamelogic.boots[i]
                    tile_id = boot_images[i] if self._gamelogic.boots[i] else TYPE_EMPTY
                    self._draw_tile(
                        buffer, ITEMS_OFFSET[0] + i * self._tile_size,
                        ITEMS_OFFSET[1] + self._tile_size, tile_id, 0
                    )

        if game_mode in (GM_NORMAL, GM_LEVELWON):
            view_port = self._gamelogic.get_view_port()
            for x_pos, x in enumerate(range(view_port.x - 4, view_port.x + 5)):
                for y_pos, y in enumerate(range(view_port.y - 4, view_port.y + 5)):
                    tile_position = Point(x, y)
                    cell = self._gamelogic.current_level.get_cell(tile_position)
                    top_tile = cell.top.id
                    bottom_tile = cell.bottom.id
                    if (data["viewport_tiles_top"][x_pos][y_pos] != top_tile or
                        (top_tile >= 0x40 and
                         data["viewport_tiles_bottom"][x_pos][y_pos] != bottom_tile)):
                        data["viewport_tiles_top"][x_pos][y_pos] = top_tile
                        data["viewport_tiles_bottom"][x_pos][y_pos] = bottom_tile
                        self._draw_tile(
                            buffer, x_pos * self._tile_size + VIEWPORT_OFFSET[0],
                            y_pos * self._tile_size + VIEWPORT_OFFSET[1], top_tile, bottom_tile
                        )

        self._draw_hint()
        self._draw_title_dialog()
