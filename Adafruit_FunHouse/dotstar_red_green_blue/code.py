# SPDX-FileCopyrightText: 2021 Kattni Rembor for Adafruit Industries
#
# SPDX-License-Identifier: MIT
#
"""CircuitPython DotStar red, green, blue example for FunHouse"""
import time
import board
import adafruit_dotstar

dots = adafruit_dotstar.DotStar(board.DOTSTAR_CLOCK, board.DOTSTAR_DATA, 5)
dots.brightness = 0.3

while True:
    dots.fill((255, 0, 0))
    time.sleep(0.5)
    dots.fill((0, 255, 0))
    time.sleep(0.5)
    dots.fill((0, 0, 255))
    time.sleep(0.5)
