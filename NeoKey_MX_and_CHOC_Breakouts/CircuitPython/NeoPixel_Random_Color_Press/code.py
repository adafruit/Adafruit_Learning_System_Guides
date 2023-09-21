# SPDX-FileCopyrightText: 2023 Kattni Rembor for Adafruit Industries
#
# SPDX-License-Identifier: MIT

"""NeoKey Breakout Random NeoPixel Color Demo"""

import random
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

# --- SET UP AND CODE ---
# Number of NeoPixels. This will always match the number of breakouts and
# therefore the number of key pins listed.
NUM_PIXELS = len(KEY_PINS)

# Create NeoPixel object.
pixels = neopixel.NeoPixel(PIXEL_PIN, NUM_PIXELS, brightness=BRIGHTNESS)

# Create keypad object.
keys = keypad.Keys(KEY_PINS, value_when_pressed=False, pull=True)

while True:
    # Begin getting key events.
    event = keys.events.get()
    # If there is a key press event, run this block.
    if event and event.pressed:
        # Print the key number of the pressed key.
        print(f"Key {event.key_number} pressed!")
        # Light up the corresponding NeoPixel to a random color.
        pixels[event.key_number] = colorwheel(random.randint(0, 255))
