# SPDX-FileCopyrightText: 2021 Trevor Beaton for Adafruit Industries
#
# SPDX-License-Identifier: MIT

import time
import board
import neopixel

pixels = neopixel.NeoPixel(board.NEOPIXEL, 10, brightness=0.2, auto_write=False)
PURPLE = (10, 0, 25)
PINK = (25, 0, 10)
OFF = (0,0,0)

while True:
    pixels.fill(PURPLE)
    pixels.show()
    time.sleep(0.5)
    pixels.fill(OFF)
    pixels.show()
    time.sleep(0.5)
    pixels.fill(PINK)
    pixels.show()
    time.sleep(0.5)
    pixels.fill(OFF)
    pixels.show()
    time.sleep(0.5)
