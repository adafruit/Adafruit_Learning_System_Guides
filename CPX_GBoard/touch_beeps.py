"""
Circuit Playground Express GBoard: capacitive touch generating tones

Adafruit invests time and resources providing this open source code.
Please support Adafruit and open source hardware by purchasing
products from Adafruit!

Written by Dave Astels for Adafruit Industries
Copyright (c) 2018 Adafruit Industries
Licensed under the MIT license.

All text above must be included in any redistribution.
"""

import time
from adafruit_circuitplayground.express import cpx

DOT_DURATION = 0.20
DASH_DURATION = 0.5

cpx.adjust_touch_threshold(600)

def touch_a():
    return cpx.touch_A4

def touch_b():
    return cpx.touch_A3

while True:
    if touch_a():
        cpx.play_tone(4000, DOT_DURATION)
        time.sleep(0.1)
        while touch_a():
            pass
    elif touch_b():
        cpx.play_tone(4000, DASH_DURATION)
        time.sleep(0.1)
        while touch_b():
            pass
