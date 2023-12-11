# SPDX-FileCopyrightText: 2020 Melissa LeBlanc-Williams for Adafruit Industries
# SPDX-FileCopyrightText: 2020 Erin St Blaine for Adafruit Industries
#
# SPDX-License-Identifier: MIT

"""
Motion-sensing Animation Example using the Matrix Portal and 64 x 32 LED matrix display
Written by Melissa LeBlanc-Williams and Erin St Blaine for Adafruit Industries
A VL6180X sensor causes a sprite sheet animation to play
"""

import time
import os
import board
import busio
import displayio
from digitalio import DigitalInOut, Pull
from adafruit_matrixportal.matrix import Matrix
from adafruit_debouncer import Debouncer
import adafruit_vl6180x
# pylint: disable=global-statement
# Create I2C bus.
i2c = busio.I2C(board.SCL, board.SDA)

# Create sensor instance.
sensor = adafruit_vl6180x.VL6180X(i2c)

SPRITESHEET_FOLDER = "/bmps"
DEFAULT_FRAME_DURATION = 0.1  # 100ms
ANIMATION_DURATION = 5
AUTO_ADVANCE_LOOPS = 1
THRESHOLD = 20

# --- Display setup ---
matrix = Matrix(bit_depth=4)
sprite_group = displayio.Group()
matrix.display.root_group = sprite_group

# --- Button setup ---
pin_down = DigitalInOut(board.BUTTON_DOWN)
pin_down.switch_to_input(pull=Pull.UP)
button_down = Debouncer(pin_down)
pin_up = DigitalInOut(board.BUTTON_UP)
pin_up.switch_to_input(pull=Pull.UP)
button_up = Debouncer(pin_up)

AUTO_ADVANCE = True

file_list = sorted(
    [
        f
        for f in os.listdir(SPRITESHEET_FOLDER)
        if (f.endswith(".bmp") and not f.startswith("."))
    ]
)

if len(file_list) == 0:
    raise RuntimeError("No images found")

CURRENT_IMAGE = None
CURRENT_FRAME = 0
CURRENT_LOOP = 0
FRAME_COUNT = 0
FRAME_DURATION = DEFAULT_FRAME_DURATION


def load_image():
    """
    Load an image as a sprite
    """
    # pylint: disable=global-statement
    global CURRENT_FRAME, CURRENT_LOOP, FRAME_COUNT, FRAME_DURATION
    while sprite_group:
        sprite_group.pop()

    filename = SPRITESHEET_FOLDER + "/" + file_list[CURRENT_IMAGE]

    # CircuitPython 6 & 7 compatible
    bitmap = displayio.OnDiskBitmap(open(filename, "rb"))
    sprite = displayio.TileGrid(
        bitmap,
        pixel_shader=getattr(bitmap, 'pixel_shader', displayio.ColorConverter()),
        tile_width=bitmap.width,
        tile_height=matrix.display.height,
    )

    # # CircuitPython 7+ compatible
    # bitmap = displayio.OnDiskBitmap(filename)
    # sprite = displayio.TileGrid(
    #     bitmap,
    #     pixel_shader=bitmap.pixel_shader,
    #     tile_width=bitmap.width,
    #     tile_height=matrix.display.height,
    # )

    sprite_group.append(sprite)

    FRAME_COUNT = int(bitmap.height / matrix.display.height)
    FRAME_DURATION = DEFAULT_FRAME_DURATION
    CURRENT_FRAME = 0
    CURRENT_LOOP = 0


def advance_image():
    """
    Advance to the next image in the list and loop back at the end
    """
    # pylint: disable=global-statement
    global CURRENT_IMAGE
    if CURRENT_IMAGE is not None:
        CURRENT_IMAGE += 1
    if CURRENT_IMAGE is None or CURRENT_IMAGE >= len(file_list):
        CURRENT_IMAGE = 0
    load_image()

def advance_frame():
    """Advance the frame"""
    # pylint: disable=global-statement
    global CURRENT_FRAME, CURRENT_LOOP
    CURRENT_FRAME = CURRENT_FRAME + 1
    if CURRENT_FRAME >= FRAME_COUNT:
        CURRENT_FRAME = 0
        CURRENT_LOOP = CURRENT_LOOP + 1
    sprite_group[0][0] = CURRENT_FRAME

def load_list_image(item):
    """Load the list item"""
    global CURRENT_IMAGE
    CURRENT_IMAGE = item
    load_image()

def load_tipsy():
    """Load the .bmp image"""
    load_list_image(1)

def play_thankyou():
    """load the thank you image"""
    load_list_image(0)
    while CURRENT_LOOP <= AUTO_ADVANCE_LOOPS:
        advance_frame()
        time.sleep(FRAME_DURATION)


advance_image()

while True:
    if sensor.range < THRESHOLD:
        play_thankyou()
    else:
        load_tipsy()
