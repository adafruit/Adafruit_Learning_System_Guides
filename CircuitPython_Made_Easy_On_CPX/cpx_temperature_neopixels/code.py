# SPDX-FileCopyrightText: 2018 Kattni Rembor for Adafruit Industries
#
# SPDX-License-Identifier: MIT

import time
from adafruit_circuitplayground.express import cpx
import simpleio

cpx.pixels.auto_write = False
cpx.pixels.brightness = 0.3

# Set these based on your ambient temperature for best results!
minimum_temp = 24
maximum_temp = 30

while True:
    # temperature value remapped to pixel position
    peak = simpleio.map_range(cpx.temperature, minimum_temp, maximum_temp, 0, 10)
    print(cpx.temperature)
    print(int(peak))

    for i in range(0, 10, 1):
        if i <= peak:
            cpx.pixels[i] = (0, 255, 255)
        else:
            cpx.pixels[i] = (0, 0, 0)
    cpx.pixels.show()
    time.sleep(0.05)
