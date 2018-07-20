"""
Circuit Playground Express GBoard: capacitive touch generating keycodes

Adafruit invests time and resources providing this open source code.
Please support Adafruit and open source hardware by purchasing
products from Adafruit!

Written by Dave Astels for Adafruit Industries
Copyright (c) 2018 Adafruit Industries
Licensed under the MIT license.

All text above must be included in any redistribution.
"""

from adafruit_circuitplayground.express import cpx
from adafruit_hid.keyboard import Keyboard
from adafruit_hid.keycode import Keycode

DOT_DURATION = 0.25
DASH_DURATION = 0.5

kbd = Keyboard()
cpx.adjust_touch_threshold(600)

def touch_a():
    return cpx.touch_A4

def touch_b():
    return cpx.touch_A3

while True:
    if touch_a():
        kbd.send(Keycode.PERIOD)
        while touch_a():
            pass
    elif touch_b():
        kbd.send(Keycode.MINUS)
        while touch_b():
            pass
