# SPDX-FileCopyrightText: 2018 Dave Astels for Adafruit Industries
#
# SPDX-License-Identifier: MIT

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

# You can adjust this to get the level of sensitivity you want.
cpx.adjust_touch_threshold(100)

while True:
    if cpx.touch_A4:
        cpx.play_tone(4000, DOT_DURATION)
        time.sleep(0.1)
        while cpx.touch_A4:
            pass
    elif cpx.touch_A3:
        cpx.play_tone(4000, DASH_DURATION)
        time.sleep(0.1)
        while cpx.touch_A3:
            pass
