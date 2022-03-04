# SPDX-FileCopyrightText: 2021 Anne Barela for Adafruit Industries
# SPDX-License-Identifier: MIT
"""
CircuitPython DotStar red, green, blue, brightness control example.
"""
import time
import board
import adafruit_dotstar

dot = adafruit_dotstar.DotStar(board.DOTSTAR_CLOCK, board.DOTSTAR_DATA, 1)
dot.brightness = 0.3

while True:
    dot.fill((255, 0, 0))  # Red
    time.sleep(0.5)
    dot.fill((0, 255, 0))  # Green
    time.sleep(0.5)
    dot.fill((0, 0, 255))  # Blue
    time.sleep(0.5)
