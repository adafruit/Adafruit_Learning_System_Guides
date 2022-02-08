# SPDX-FileCopyrightText: 2021 Kattni Rembor for Adafruit Industries
# SPDX-License-Identifier: Unlicense
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
        for led in range(1):
            dot_index = (led * 256 // 1) + color_value
            dot[led] = colorwheel(dot_index & 255)
        dot.show()
        time.sleep(delay)


while True:
    rainbow(0.02)
