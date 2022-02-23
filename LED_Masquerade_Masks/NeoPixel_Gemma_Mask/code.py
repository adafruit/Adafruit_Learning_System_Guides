# SPDX-FileCopyrightText: 2017 Phillip Burgess for Adafruit Industries
#
# SPDX-License-Identifier: MIT

import time
from rainbowio import colorwheel
import board
import neopixel

numpix = 5  # Number of NeoPixels
pixpin = board.D1  # Pin where NeoPixels are connected
hue = 0  # Starting color
strip = neopixel.NeoPixel(pixpin, numpix, brightness=0.4)

while True:  # Loop forever...
    for i in range(numpix):
        strip[i] = colorwheel((hue + i * 8) & 255)
    strip.write()
    time.sleep(0.02)  # 20 ms = ~50 fps
    hue = (hue + 1) & 255  # Increment hue and 'wrap around' at 255
