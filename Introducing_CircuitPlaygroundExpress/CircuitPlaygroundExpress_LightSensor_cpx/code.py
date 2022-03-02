# SPDX-FileCopyrightText: 2017 Kattni Rembor for Adafruit Industries
#
# SPDX-License-Identifier: MIT

# CircuitPlaygroundExpress_LightSensor
# reads the on-board light sensor and graphs the brighness with NeoPixels

import time

from adafruit_circuitplayground.express import cpx
from simpleio import map_range

cpx.pixels.brightness = 0.05

while True:
    # light value remaped to pixel position
    peak = map_range(cpx.light, 10, 325, 0, 9)
    print(cpx.light)
    print(int(peak))

    for i in range(0, 9, 1):
        if i <= peak:
            cpx.pixels[i] = (0, 255, 0)
        else:
            cpx.pixels[i] = (0, 0, 0)

    time.sleep(0.01)
