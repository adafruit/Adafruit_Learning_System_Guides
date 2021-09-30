# SPDX-FileCopyrightText: 2017 by Mikey Sklar for Adafruit Industries
#
# SPDX-License-Identifier: MIT

import time
import board
import neopixel
from rainbowio import colorwheel
from digitalio import DigitalInOut, Direction

pixpin = board.D1
numpix = 8

led = DigitalInOut(board.D13)
led.direction = Direction.OUTPUT

strip = neopixel.NeoPixel(pixpin, numpix, brightness=1, auto_write=True)


def rainbow_cycle(wait):
    for j in range(255 * 5):
        for i in range(len(strip)):
            idx = int((i * 256 / len(strip)) + j)
            strip[i] = colorwheel(idx & 255)
        time.sleep(wait)


def rainbow(wait):
    for j in range(255):
        for i in range(len(strip)):
            idx = int(i + j)
            strip[i] = colorwheel(idx & 255)
        time.sleep(wait)


while True:
    rainbow_cycle(0.05)
