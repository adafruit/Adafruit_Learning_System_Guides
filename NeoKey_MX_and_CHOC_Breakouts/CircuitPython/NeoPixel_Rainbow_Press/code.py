# SPDX-FileCopyrightText: 2023 Kattni Rembor for Adafruit Industries
# SPDX-FileCopyrightText: 2023 Dan Halbert for Adafruit Industries
#
# SPDX-License-Identifier: MIT

"""NeoKey Breakout NeoPixel Rainbow Cycle Demo"""

import time
import board
import keypad
import neopixel
from rainbowio import colorwheel

# --- CONFIGURATION ---
# NeoPixel brightness. Must be a float or integer between 0.0 and 1.0, where 0 is off and
# 1 is maximum brightness. Defaults to 0.3.
BRIGHTNESS = 0.3

# NeoPixel and key switch pins. If using different pins, update to match your wiring setup.
# pylint: disable=simplifiable-condition
# Check to see if a Raspberry Pi is present, and set the appropriate pins.
if "CE0" and "CE1" in dir(board):  # These pins are Pi-specific.
    PIXEL_PIN = board.D18
    KEY_PINS = (
        board.D4,
        board.D17,
    )
# Otherwise, assume a microcontroller, and set the appropriate pins.
else:
    PIXEL_PIN = board.A3
    KEY_PINS = (
        board.A1,
        board.A2,
    )

# --- SETUP AND CODE ---
# Number of NeoPixels. This will always match the number of breakouts and
# therefore the number of key pins listed.
NUM_PIXELS = len(KEY_PINS)

# Create NeoPixel object.
pixels = neopixel.NeoPixel(PIXEL_PIN, NUM_PIXELS, brightness=BRIGHTNESS)

# Create keypad object.
keys = keypad.Keys(KEY_PINS, value_when_pressed=False, pull=True)

# Create two lists.
# The `pressed` list is used to track the key press state.
pressed = [False] * NUM_PIXELS
# The `color_value` list is used to track the current color value for a specific NeoPixel.
color_value = [0] * NUM_PIXELS

while True:
    # Begin getting key events.
    event = keys.events.get()
    if event:
        # Remember the last state of the key when pressed.
        pressed[event.key_number] = event.pressed

    # Advance the rainbow for the key that is currently pressed.
    for index in range(NUM_PIXELS):
        if pressed[index]:
            # Increase the color value by 1.
            color_value[index] += 1
            # Set the pixel color to the current color value.
            pixels[index] = colorwheel(color_value[index])

    time.sleep(0.01)
