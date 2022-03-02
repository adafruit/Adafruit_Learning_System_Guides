# SPDX-FileCopyrightText: 2019 Kattni Rembor for Adafruit Industries
#
# SPDX-License-Identifier: MIT

"""Simple rainbow example for 30-pixel NeoPixel strip"""
import digitalio
import board
from rainbowio import colorwheel
import neopixel

NUM_PIXELS = 30  # NeoPixel strip length (in pixels)

enable = digitalio.DigitalInOut(board.D10)
enable.direction = digitalio.Direction.OUTPUT
enable.value = True

strip = neopixel.NeoPixel(board.D5, NUM_PIXELS, brightness=1)

while True:
    for i in range(255):
        strip.fill((colorwheel(i)))
