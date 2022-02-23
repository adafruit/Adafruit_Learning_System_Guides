# SPDX-FileCopyrightText: 2018 Dave Astels for Adafruit Industries
#
# SPDX-License-Identifier: MIT

"""
Circuit Playground Express GBoard: onboard buttons generating tones

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

while True:
    if cpx.button_a:
        cpx.play_tone(4000, DOT_DURATION)
        time.sleep(0.1)
        while cpx.button_a:
            pass
    elif cpx.button_b:
        cpx.play_tone(4000, DASH_DURATION)
        time.sleep(0.1)
        while cpx.button_b:
            pass
