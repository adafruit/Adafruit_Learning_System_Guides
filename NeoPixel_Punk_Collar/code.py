# SPDX-FileCopyrightText: 2017 Limor Fried for Adafruit Industries
#
# SPDX-License-Identifier: MIT

import time
from rainbowio import colorwheel
import board
import neopixel
from digitalio import DigitalInOut, Direction

pixpin = board.D1
numpix = 5

led = DigitalInOut(board.D13)
led.direction = Direction.OUTPUT

strip = neopixel.NeoPixel(pixpin, numpix, brightness=1, auto_write=True)


def colorWipe(color, wait):
    for j in range(len(strip)):
        strip[j] = (color)
        time.sleep(wait)


def rainbow_cycle(wait):
    for j in range(255):
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
    colorWipe((255, 0, 0), .1)  # red and delay
    colorWipe((0, 255, 0), .1)  # green and delay
    colorWipe((0, 0, 255), .1)  # blue and delay

    rainbow(0.05)
    rainbow_cycle(0.05)
