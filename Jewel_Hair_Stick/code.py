# SPDX-FileCopyrightText: 2017 Leslie Birch for Adafruit Industries
#
# SPDX-License-Identifier: MIT

# Jewel Hairstick by Leslie Birch for Adafruit Industries
# Based on NeoPixel Library by Adafruit

import time

import board
import neopixel
from digitalio import DigitalInOut, Direction

pixpin = board.D1
numpix = 7

led = DigitalInOut(board.D13)
led.direction = Direction.OUTPUT

# defaults to RGB|GRB Neopixels
strip = neopixel.NeoPixel(pixpin, numpix, brightness=.1, auto_write=True)
# uncomment the following two lines for RGBW Neopixels
# strip = neopixel.NeoPixel(
#   pixpin, numpix, bpp=4, brightness=.3, auto_write=True)

# You can have fun here changing the colors for the code
color1 = (236, 79, 100)  # Salmon Pink
color2 = (246, 216, 180)  # Cream
color3 = (174, 113, 208)  # Lavendar
color4 = (182, 31, 40)  # Red
color5 = (91, 44, 86)  # Purple

while True:
    # the first number is the pixel number for Jewel. O is the center one
    strip[1] = color1
    strip[2] = color1
    strip[3] = color1
    strip[4] = color1
    strip[5] = color1
    strip[6] = color1
    strip[0] = color2
    time.sleep(3)

    strip[1] = color2
    strip[2] = color2
    strip[3] = color2
    strip[4] = color2
    strip[5] = color2
    strip[6] = color2
    strip[0] = color3
    time.sleep(3)

    strip[1] = color3
    strip[2] = color3
    strip[3] = color3
    strip[4] = color3
    strip[5] = color3
    strip[6] = color3
    strip[0] = color4
    time.sleep(3)

    strip[1] = color4
    strip[2] = color4
    strip[3] = color4
    strip[4] = color4
    strip[5] = color4
    strip[6] = color4
    strip[0] = color5
    time.sleep(3)
