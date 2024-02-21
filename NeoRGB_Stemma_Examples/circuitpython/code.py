# SPDX-FileCopyrightText: 2024 Liz Clark for Adafruit Industries
#
# SPDX-License-Identifier: MIT

import time
import board
from rainbowio import colorwheel
import neopixel

num_pixels = 1
# pylint: disable=simplifiable-condition
# check to see if its a raspberry pi
if "CE0" and "CE1" in dir(board):  # pi only zone
    pixel_pin = board.D18
# otherwise assume a microcontroller
else:
    pixel_pin = board.D5

pixels = neopixel.NeoPixel(pixel_pin, num_pixels)

color_offset = 0

while True:
    for i in range(num_pixels):
        rc_index = (i * 256 // num_pixels) + color_offset
        pixels[i] = colorwheel(rc_index & 255)
    pixels.show()
    color_offset += 1
    time.sleep(0.01)
