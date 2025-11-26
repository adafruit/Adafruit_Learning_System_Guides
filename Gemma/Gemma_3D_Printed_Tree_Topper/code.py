# SPDX-FileCopyrightText: 2017 Phillip Burgess for Adafruit Industries
#
# SPDX-License-Identifier: MIT

import time

import board
import neopixel

try:
    import urandom as random  # for v1.0 API support
except ImportError:
    import random

numpix = 36  # Number of NeoPixels
pixpin = board.D1  # Pin where NeoPixels are connected
strip = neopixel.NeoPixel(pixpin, numpix, brightness=1.0)

mode = 0  # Current animation effect
offset = 0  # Position of spinner animation
color = [160, 0, 160]  # RGB color - purple
prevtime = time.monotonic()  # Time of last animation mode switch

while True:  # Loop forever...

    if mode == 0:  # Random sparkles - lights just one LED at a time
        i = random.randint(0, numpix - 1)  # Choose random pixel
        strip[i] = color  # Set it to current color
        strip.write()  # Refresh LED states
        # Set same pixel to "off" color now but DON'T refresh...
        # it stays on for now...bot this and the next random
        # pixel will be refreshed on the next pass.
        strip[i] = [0, 0, 0]
        time.sleep(0.008)  # 8 millisecond delay
    elif mode == 1:  # Spinny wheel (4 LEDs on at a time)
        for i in range(numpix):  # For each LED...
            if ((offset + i) & 7) < 2:  # 2 pixels out of 8...
                strip[i] = color  # are set to current color
            else:
                strip[i] = [0, 0, 0]  # other pixels are off
        strip.write()  # Refresh LED states
        time.sleep(0.08)  # 80 millisecond delay
        offset += 1  # Shift animation by 1 pixel on next frame
        if offset >= 8:
            offset = 0
    # Additional animation modes could be added here!

    t = time.monotonic()  # Current time in seconds
    if (t - prevtime) >= 8:  # Every 8 seconds...
        mode += 1  # Advance to next mode
        if mode > 1:  # End of modes?
            mode = 0  # Start over from beginning
        strip.fill([0, 0, 0])  # Turn off all pixels
        prevtime = t  # Record time of last mode change
