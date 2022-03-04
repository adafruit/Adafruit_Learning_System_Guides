# SPDX-FileCopyrightText: 2021 Kattni Rembor for Adafruit Industries
# SPDX-License-Identifier: MIT
"""
CircuitPython NeoPixel Blink example - blinking the built-in NeoPixel(s).

This example is meant for boards that have built-in NeoPixel LEDs but do not have a little
red LED. If a little red LED is present, use the standard Blink template and example.

Update NUMBER_OF_PIXELS to the match the number of built-in NeoPixels on the board.

DO NOT INCLUDE THE pylint: disable LINE IN THE GUIDE CODE. It is present only to deal with the
NUMBER_OF_PIXELS variable being undefined in this pseudo-code. As you will be updating the variable
in the guide, you will not need the pylint: disable.

For example:
If you are using a QT Py, change NUMBER_OF_PIXELS to 1.
If using a Neo Trinkey, change NUMBER_OF_PIXELS to 4.
"""
# pylint: disable=undefined-variable

import time
import board
import neopixel

pixel = neopixel.NeoPixel(board.NEOPIXEL, NUMBER_OF_PIXELS)

while True:
    pixel.fill((255, 0, 0))
    time.sleep(0.5)
    pixel.fill((0, 0, 0))
    time.sleep(0.5)
