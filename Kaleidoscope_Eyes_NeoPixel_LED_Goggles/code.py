# SPDX-FileCopyrightText: 2017 Mikey Sklar for Adafruit Industries
#
# SPDX-License-Identifier: MIT

#
# Kaleidoscope_Eyes_NeoPixel_LED_Goggles.py
#
import time

import board
import neopixel

try:
    import urandom as random  # for v1.0 API support
except ImportError:
    import random

numpix = 32  # Number of NeoPixels
pixpin = board.D0  # Pin where NeoPixels are connected

mode = 0  # Current animation effect
offset = 0  # Position of spinny eyes

rgb_colors = ([255, 0, 0],  # red
              [0, 255, 0],  # green
              [0, 0, 255])  # blue

rgb_idx = 0  # index counter - primary color we are on
color = rgb_colors[rgb_idx]
prevtime = 0

pixels = neopixel.NeoPixel(pixpin, numpix, brightness=.3, auto_write=False)

prevtime = time.monotonic()

while True:
    i = 0
    t = 0

    # Random sparks - just one LED on at a time!
    if mode == 0:
        i = random.randint(0, (numpix - 1))
        pixels[i] = color
        pixels.write()
        time.sleep(0.01)
        pixels[i] = (0, 0, 0)

    # Spinny wheels (8 LEDs on at a time)
    elif mode == 1:
        for i in range(0, numpix):
            c = 0

            # 4 pixels on...
            if ((offset + i) & 7) < 2:
                c = color

            pixels[i] = c  # First eye
            pixels[(numpix - 1) - i] = c  # Second eye (flipped)

        pixels.write()
        offset += 1
        time.sleep(0.05)

    t = time.monotonic()

    if (t - prevtime) > 8:  # Every 8 seconds...
        mode += 1  # Next mode
        if mode > 1:  # End of modes?
            mode = 0  # Start modes over

        if rgb_idx > 2:  # reset R-->G-->B rotation
            rgb_idx = 0

        color = rgb_colors[rgb_idx]  # next color assignment
        rgb_idx += 1

        for i in range(0, numpix):
            pixels[i] = (0, 0, 0)

        prevtime = t
