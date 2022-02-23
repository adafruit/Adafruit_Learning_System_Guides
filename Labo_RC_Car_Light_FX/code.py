# SPDX-FileCopyrightText: 2018 Collin Cunningham for Adafruit Industries
#
# SPDX-License-Identifier: MIT

import board
import neopixel
from adafruit_circuitplayground.express import cpx

pixels = neopixel.NeoPixel(board.NEOPIXEL, 10, brightness=0.1, auto_write=True)
pixels.fill(0)

while True:

    x, y, z = cpx.acceleration  # read acceleromter
    r, g, b = 0, 0, 0

    if abs(x) > 4.0:
        r = 255
    if abs(y) > 2.0:
        g = 255
    if z > -6.0 or z < -12.0:
        b = 255

    pixels.fill((r, g, b))
