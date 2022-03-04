# SPDX-FileCopyrightText: 2021 Kattni Rembor for Adafruit Industries
# SPDX-License-Identifier: MIT
"""
CircuitPython DotStar red, green, blue, brightness control example - multiple DotStars.

This example is meant for boards that have multiple built-in DotStar LEDs.

Update NUMBER_OF_PIXELS to the match the number of built-in DotStars on the board.

DO NOT INCLUDE THE pylint: disable LINE IN THE GUIDE CODE. It is present only to deal with the
NUMBER_OF_PIXELS variable being undefined in this pseudo-code. As you will be updating the variable
in the guide, you will not need the pylint: disable.

For example:
If you are using a FunHouse, change NUMBER_OF_PIXELS to 5.
"""
# pylint: disable=undefined-variable

import time
import board
import adafruit_dotstar

dots = adafruit_dotstar.DotStar(board.DOTSTAR_CLOCK, board.DOTSTAR_DATA, NUMBER_OF_PIXELS)
dots.brightness = 0.3

while True:
    dots.fill((255, 0, 0))
    time.sleep(0.5)
    dots.fill((0, 255, 0))
    time.sleep(0.5)
    dots.fill((0, 0, 255))
    time.sleep(0.5)
