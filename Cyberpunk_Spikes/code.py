# SPDX-FileCopyrightText: 2017 Mikey Sklar for Adafruit Industries
#
# SPDX-License-Identifier: MIT

import time
from rainbowio import colorwheel
import board
import neopixel
from digitalio import DigitalInOut, Direction

try:
    import urandom as random
except ImportError:
    import random

pixpin = board.D1
numpix = 16

led = DigitalInOut(board.D13)
led.direction = Direction.OUTPUT

strip = neopixel.NeoPixel(pixpin, numpix, brightness=.2, auto_write=True)

colors = [
    [232, 100, 255],  # Purple
    [200, 200, 20],  # Yellow
    [30, 200, 200],  # Blue
]


# Fill the dots one after the other with a color


def colorWipe(color, wait):
    for j in range(len(strip)):
        strip[j] = (color)
        time.sleep(wait)


def rainbow(wait):
    for j in range(255):
        for i in range(len(strip)):
            idx = int(i + j)
            strip[i] = colorwheel(idx & 255)
        time.sleep(wait)


# Slightly different, this makes the rainbow equally distributed throughout


def rainbow_cycle(wait):
    for j in range(255 * 5):
        for i in range(len(strip)):
            idx = int((i * 256 / len(strip)) + j)
            strip[i] = colorwheel(idx & 255)
        time.sleep(wait)


def flash_random(wait, howmany):
    for _ in range(howmany):

        c = random.randint(0, len(colors) - 1)  # Choose random color index
        j = random.randint(0, numpix - 1)  # Choose random pixel
        strip[j] = colors[c]  # Set pixel to color

        for i in range(1, 5):
            strip.brightness = i / 5.0  # Ramp up brightness
            time.sleep(wait)

        for i in range(5, 0, -1):
            strip.brightness = i / 5.0  # Ramp down brightness
            strip[j] = [0, 0, 0]  # Set pixel to 'off'
            time.sleep(wait)


while True:
    # first number is 'wait' delay, shorter num == shorter twinkle
    flash_random(.01, 8)
    # second number is how many neopixels to simultaneously light up
    flash_random(.01, 5)
    flash_random(.01, 11)

    colorWipe((232, 100, 255), .1)
    colorWipe((200, 200, 20), .1)
    colorWipe((30, 200, 200), .1)

    rainbow_cycle(0.05)
