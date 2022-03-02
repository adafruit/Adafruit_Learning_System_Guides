# SPDX-FileCopyrightText: 2017 Mikey Sklar for Adafruit Industries
#
# SPDX-License-Identifier: MIT

import time

import board
import neopixel
from digitalio import DigitalInOut, Direction

pix_pin = board.D1
num_pix = 5

led = DigitalInOut(board.D13)
led.direction = Direction.OUTPUT

strip = neopixel.NeoPixel(pix_pin, num_pix, brightness=1, auto_write=True)


def color_wipe(color, wait):
    for j in range(len(strip)):
        strip[j] = (color)
        time.sleep(wait)


while True:
    color_wipe((50, 0, 50), .1)  # Purple LEDs
