"""
Circuit Playground Express GBoard: arcade buttons generating keycodes

Adafruit invests time and resources providing this open source code.
Please support Adafruit and open source hardware by purchasing
products from Adafruit!

Written by Dave Astels for Adafruit Industries
Copyright (c) 2018 Adafruit Industries
Licensed under the MIT license.

All text above must be included in any redistribution.
"""

import board
import usb_hid
from adafruit_hid.keyboard import Keyboard
from adafruit_hid.keycode import Keycode
from digitalio import DigitalInOut, Direction, Pull

DOT_DURATION = 0.25
DASH_DURATION = 0.5

button_a = DigitalInOut(board.A4)
button_a.direction = Direction.INPUT
button_a.pull = Pull.UP

button_b = DigitalInOut(board.A3)
button_b.direction = Direction.INPUT
button_b.pull = Pull.UP

kbd = Keyboard(usb_hid.devices)


def touch_a():
    return not button_a.value


def touch_b():
    return not button_b.value


while True:
    if touch_a():
        kbd.send(Keycode.PERIOD)
        while touch_a():
            pass
    elif touch_b():
        kbd.send(Keycode.MINUS)
        while touch_b():
            pass
