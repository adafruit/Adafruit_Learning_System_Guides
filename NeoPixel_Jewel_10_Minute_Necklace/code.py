# SPDX-FileCopyrightText: 2017 Mikey Sklar for Adafruit Industries
#
# SPDX-License-Identifier: MIT

import time
from rainbowio import colorwheel
import board
import neopixel

pixpin = board.D1
numpix = 7

pixels = neopixel.NeoPixel(pixpin, numpix, brightness=.3, auto_write=False)

rgb_colors = ([179, 0, 0],
              [0, 179, 0],
              [0, 0, 0])

rgb_idx = 0  # index counter - primary color we are on
color = (0, 164, 179)  # Starting color
mode = 0  # Current animation effect
offset = 0
prevtime = 0


def rainbow_cycle(wait):
    for j in range(255 * 6):  # 6 cycles of all colors on colorwheel
        for r in range(len(pixels)):
            idx = int((r * 255 / len(pixels)) + j)
            pixels[r] = colorwheel(idx & 255)
        pixels.write()
        time.sleep(wait)


def rainbow(wait):
    for j in range(255):
        for index in range(len(pixels)):
            idx = int(index + j)
            pixels[index] = colorwheel(idx & 255)
        pixels.write()
        time.sleep(wait)


def rainbow_cycle_slow(wait):
    for j in range(255 * 3):  # 3 cycles of all colors on colorwheel
        for r in range(len(pixels)):
            idx = int((r * 255 / len(pixels)) + j)
            pixels[r] = colorwheel(idx & 255)
        pixels.write()
        time.sleep(wait)


def rainbow_hold(wait):
    for j in range(255 * 1):  # 3 cycles of all colors on colorwheel
        for r in range(len(pixels)):
            idx = int((r * 255 / len(pixels)) + j)
            pixels[r] = colorwheel(idx & 255)
    pixels.write()
    time.sleep(wait)


while True:

    if mode == 0:  # rainbow hold
        rainbow_hold(0.02)
        time.sleep(.5)

    elif mode == 1:  # rainbow cycle slow
        rainbow_cycle_slow(0.02)
        time.sleep(0.05)

    elif mode == 2:  # rainbow cycle fast
        rainbow_cycle(0.005)
        time.sleep(0.050)

    t = time.monotonic()

    if (t - prevtime) > 8:  # Every 8 seconds...
        mode += 1  # Next mode
        if mode > 2:  # End of modes?
            mode = 0  # Start modes over

        if rgb_idx > 2:  # reset R-->G-->B rotation
            rgb_idx = 0

        color = rgb_colors[rgb_idx]  # next color assignment
        rgb_idx += 1

        for i in range(numpix):
            pixels[i] = (0, 0, 0)

        prevtime = t
