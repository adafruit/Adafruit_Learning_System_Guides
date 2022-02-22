# SPDX-FileCopyrightText: 2018 Kattni Rembor for Adafruit Industries
#
# SPDX-License-Identifier: MIT

import time
from rainbowio import colorwheel
import adafruit_dotstar
import board

# For Trinket M0, Gemma M0, and ItsyBitsy M0 Express
led = adafruit_dotstar.DotStar(board.APA102_SCK, board.APA102_MOSI, 1)


# For Feather M0 Express, Metro M0 Express, and Circuit Playground Express
# led = neopixel.NeoPixel(board.NEOPIXEL, 1)

led.brightness = 0.3

i = 0
while True:
    i = (i + 1) % 256  # run from 0 to 255
    led.fill(colorwheel(i))
    time.sleep(0.1)
