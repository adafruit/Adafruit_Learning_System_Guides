# SPDX-FileCopyrightText: 2023 Kattni Rembor for Adafruit Industries
#
# SPDX-License-Identifier: MIT

"""NeoKey Breakout HID Demo"""

import time
import board
import keypad
import usb_hid
import neopixel
from adafruit_hid.keyboard import Keyboard
from adafruit_hid.keycode import Keycode

# --- CONFIGURATION ---
# Keycode to send on key press.
SEND_ON_PRESS = (
    Keycode.B,
    Keycode.THREE,
)

# NeoPixel colors for each key when pressed.
COLORS = (
    (255, 255, 0),  # Yellow
    (0, 255, 255),  # Cyan
)

# NeoPixel brightness. Must be a float or integer between 0.0 and 1.0, where 0 is off and
# 1 is maximum brightness. Defaults to 0.3.
BRIGHTNESS = 0.3

# NeoPixel and key switch pins. Update to match your wiring setup.
PIXEL_PIN = board.A3
KEY_PINS = (
    board.A1,
    board.A2,
)

# --- SETUP AND CODE ---
# Number of NeoPixels. This will always match the number of breakouts and
# therefore the number of key pins listed.
NUM_PIXELS = len(KEY_PINS)

# Create keyboard object.
time.sleep(1)  # Delay to avoid a race condition on some systems.
keyboard = Keyboard(usb_hid.devices)

# Create NeoPixel object.
pixels = neopixel.NeoPixel(PIXEL_PIN, NUM_PIXELS, brightness=BRIGHTNESS)

# Create keypad object.
keys = keypad.Keys(KEY_PINS, value_when_pressed=False, pull=True)

while True:
    # Begin getting key events.
    event = keys.events.get()

    # If there is a key press event, run this block.
    if event and event.pressed:
        # Save the number of the key pressed to `key_number` to use in multiple places.
        key_number = event.key_number
        # Light up the corresponding NeoPixel to the appropriate color in the `COLORS` tuple.
        pixels[key_number] = COLORS[key_number]
        # Send the appropriate `Keycode` as identified in the `SEND_ON_PRESS` tuple.
        keyboard.press(SEND_ON_PRESS[key_number])

    # If there is a key released event, run this block.
    if event and event.released:
        # Turn off the LEDs.
        pixels.fill((0, 0, 0))
        # Report that the key switch has been released.
        keyboard.release_all()
