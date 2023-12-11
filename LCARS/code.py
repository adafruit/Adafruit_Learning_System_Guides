# SPDX-FileCopyrightText: 2023 John Park for Adafruit Industries
#
# SPDX-License-Identifier: MIT
# LCARS MatrixPortal Display
# LED brigthness code by Jan Goolsbey

import time
import os
import board
import displayio
from digitalio import DigitalInOut, Pull
from simpleio import map_range  # For color brightness calculation
from adafruit_matrixportal.matrix import Matrix
from adafruit_debouncer import Debouncer

import supervisor
supervisor.runtime.autoreload = True

SPRITESHEET_FOLDER = "/bmps"
DEFAULT_FRAME_DURATION = 0.7  # 100ms
AUTO_ADVANCE_LOOPS = 3
bitmap = ""
brightness = 15  # ### Integer value from 0 to 15

# --- Display setup ---
matrix = Matrix(bit_depth=4, width=128, height=64)
sprite_group = displayio.Group()
matrix.display.root_group = sprite_group

# --- Button setup ---
pin_down = DigitalInOut(board.BUTTON_DOWN)
pin_down.switch_to_input(pull=Pull.UP)
button_down = Debouncer(pin_down)
pin_up = DigitalInOut(board.BUTTON_UP)
pin_up.switch_to_input(pull=Pull.UP)
button_up = Debouncer(pin_up)

auto_advance = False

file_list = sorted(
    [
        f
        for f in os.listdir(SPRITESHEET_FOLDER)
        if (f.endswith(".bmp") and not f.startswith("."))
    ]
)

if len(file_list) == 0:
    raise RuntimeError("No images found")

current_image = None
current_frame = 0
current_loop = 0
frame_count = 0
frame_duration = DEFAULT_FRAME_DURATION

def image_brightness(new_bright=0):
    """Calculate the white color brightness.
    Returns a white RBG888 color value proportional to `new_bright`."""
    # Scale brightness value
    bright = int(map_range(new_bright, 0, 15, 0x00, 0xFF))
    # Recombine and return a composite RGB888 value
    return (bright << 16) + (bright << 8) + bright

def load_image():
    """
    Load an image as a sprite
    """
    # pylint: disable=global-statement
    global current_frame, current_loop, frame_count, frame_duration, bitmap
    while sprite_group:
        sprite_group.pop()

    filename = SPRITESHEET_FOLDER + "/" + file_list[current_image]

    bitmap = displayio.OnDiskBitmap(filename)
    ### Change the palette value proportional to BRIGHTNESS
    bitmap.pixel_shader[1] = image_brightness(brightness)
    sprite = displayio.TileGrid(
        bitmap,
        pixel_shader=bitmap.pixel_shader,
        tile_width=bitmap.width,
        tile_height=matrix.display.height,
    )

    sprite_group.append(sprite)

    current_frame = 0
    current_loop = 0
    frame_count = int(bitmap.height / matrix.display.height)
    frame_duration = DEFAULT_FRAME_DURATION


def advance_image():
    """
    Advance to the next image in the list and loop back at the end
    """
    # pylint: disable=global-statement
    global current_image
    if current_image is not None:
        current_image += 1
    if current_image is None or current_image >= len(file_list):
        current_image = 0
    load_image()


def advance_frame():
    """
    Advance to the next frame and loop back at the end
    """
    # pylint: disable=global-statement
    global current_frame, current_loop
    current_frame = current_frame + 1
    if current_frame >= frame_count:
        current_frame = 0
        current_loop = current_loop + 1
    sprite_group[0][0] = current_frame

advance_image()

last_time = time.monotonic()


while True:
    button_down.update()
    button_up.update()
    if button_up.fell:
        advance_image()
    if button_down.fell:
        brightness = (brightness + 2) % 16
        print(brightness)
        bitmap.pixel_shader[1] = image_brightness(brightness)  # ### Change the brightness

    if time.monotonic() - last_time > frame_duration:
        advance_frame()
        last_time = time.monotonic()
