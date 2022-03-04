# SPDX-FileCopyrightText: 2021 Kattni Rembor for Adafruit Industries
# SPDX-License-Identifier: MIT
"""
CircuitPython DotStar red, green, blue, brightness control example.
"""
import time
import board
from rainbowio import colorwheel
import adafruit_dotstar

dot = adafruit_dotstar.DotStar(board.DOTSTAR_CLOCK, board.DOTSTAR_DATA, 1)
dot.brightness = 0.3


def rainbow(delay):
    for color_value in range(255):
        dot[0] = colorwheel(color_value)
        time.sleep(delay)


while True:
    rainbow(0.02)
