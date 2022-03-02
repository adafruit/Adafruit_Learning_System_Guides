# SPDX-FileCopyrightText: 2017 John Edgar Park for Adafruit Industries
#
# SPDX-License-Identifier: MIT

# Circuit Playground Light Sensor
# Reads the on-board light sensor and graphs the brightness with NeoPixels

import time
import board
import neopixel
import analogio
import simpleio

pixels = neopixel.NeoPixel(board.NEOPIXEL, 10, brightness=.05, auto_write=False)
pixels.fill((0, 0, 0))
pixels.show()

light = analogio.AnalogIn(board.LIGHT)

while True:
    # light value remapped to pixel position
    peak = simpleio.map_range(light.value, 2000, 62000, 0, 9)
    print(light.value)
    print(int(peak))

    for i in range(0, 9, 1):
        if i <= peak:
            pixels[i] = (0, 255, 0)
        else:
            pixels[i] = (0, 0, 0)
    pixels.show()

    time.sleep(0.01)
