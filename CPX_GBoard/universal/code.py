# SPDX-FileCopyrightText: 2018 Dave Astels for Adafruit Industries
#
# SPDX-License-Identifier: MIT

"""
Circuit Playground Express GBoard: universal/customizable version

Adafruit invests time and resources providing this open source code.
Please support Adafruit and open source hardware by purchasing
products from Adafruit!

Written by Dave Astels for Adafruit Industries
Copyright (c) 2018 Adafruit Industries
Licensed under the MIT license.

All text above must be included in any redistribution.
"""
# pylint: disable=unused-import

import time
from adafruit_circuitplayground.express import cpx

# Uncomment the next 2 lines if you want to use external buttons
# from digitalio import DigitalInOut, Direction, Pull
# import board

# Uncomment the next 3 lines if you want to use HID output
# from adafruit_hid.keyboard import Keyboard
# from adafruit_hid.keycode import Keycode
# import usb_hid

DOT_DURATION = 0.20
DASH_DURATION = 0.5

# You can adjust this to get the level of sensitivity you want.
# Uncomment the next line if you want to use capacitive touch.
# cpx.adjust_touch_threshold(100)

# Uncomment the next 6 lines if you want to use external buttons
# button_a = DigitalInOut(board.A4)
# button_a.direction = Direction.INPUT
# button_a.pull = Pull.UP
# button_b = DigitalInOut(board.A3)
# button_b.direction = Direction.INPUT
# button_b.pull = Pull.UP

# Uncomment the next  line if you want to use HID output
# kbd = Keyboard(usb_hid.devices)



def touch_a():
    # Uncomment the next line if you want to use the on-board buttons
    # return cpx.button_a

    # Uncomment the next line if you want to use capacitive touch
    # return cpx.touch_A4

    # Uncomment the next line if you want to use external buttons
    # return not button_a.value

    return False   # a fail-safe to keep python happy


def touch_b():
    # Uncomment the next line if you want to use the on-board buttons
    # return cpx.button_b

    # Uncomment the next line if you want to use capacitive touch
    # return cpx.touch_A3

    # Uncomment the next line if you want to use external buttons
    # return not button_b.value

    return False   # a fail-safe to keep python happy


def dot():
    # Uncomment the next 2 lines if you want tones played
    # cpx.play_tone(4000, DOT_DURATION)
    # time.sleep(0.1)

    # Uncomment the next line if you want to use HID output
    # kbd.send(Keycode.PERIOD)

    pass   # a fail-safe to keep python happy


def dash():
    # Uncomment the next 2 lines if you want tones played
    # cpx.play_tone(4000, DASH_DURATION)
    # time.sleep(0.1)

    # Uncomment the next line if you want to use HID output
    # kbd.send(Keycode.MINUS)

    pass   # a fail-safe to keep python happy


while True:
    if touch_a():
        dot()
        while touch_a():
            pass
    elif touch_b():
        dash()
        while touch_b():
            pass
