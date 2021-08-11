# SPDX-FileCopyrightText: Copyright (c) 2021 Dylan Herrada for Adafruit Industries
#
# SPDX-License-Identifier: Unlicense
import time

import usb_hid
from adafruit_hid.keyboard import Keyboard
from adafruit_hid.keyboard_layout_us import KeyboardLayoutUS
import adafruit_ducky

import touchio # pylint: disable=unused-import
import board
import neopixel
from digitalio import DigitalInOut, Pull # pylint: disable=unused-import

# Uncomment for Neo Trinkey
touch1 = touchio.TouchIn(board.TOUCH1)
touch2 = touchio.TouchIn(board.TOUCH2)

# Uncomment for NeoKey Trinkey
#button = DigitalInOut(board.SWITCH)
#button.switch_to_input(pull=Pull.DOWN)
#button_state = False

pixels = neopixel.NeoPixel(board.NEOPIXEL, 4)

pixels.fill((0xFFFFFF))

time.sleep(1)  # Sleep for a bit to avoid a race condition on some systems
keyboard = Keyboard(usb_hid.devices)
keyboard_layout = KeyboardLayoutUS(keyboard)  # We're in the US :)

duck = adafruit_ducky.Ducky("duckyscript.txt", keyboard, keyboard_layout)

result = True
running = False
while result is not False:
    #if button.value: # Uncomment for NeoKey Trinkey
    if any([touch1.value, touch2.value]): # Uncomment for Neo Trinkey
        running = not running
        if running:
            pixels.fill((0x00FF00))
        else:
            pixels.fill((0xFF0000))
        time.sleep(0.2)
    if running:
        result = duck.loop()
