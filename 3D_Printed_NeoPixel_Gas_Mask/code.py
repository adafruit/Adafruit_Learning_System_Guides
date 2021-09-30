# SPDX-FileCopyrightText: 2017 Phil Burgessr for Adafruit Industries
#
# SPDX-License-Identifier: MIT
#
import time
import board
import neopixel

try:
    import urandom as random  # for v1.0 API support
except ImportError:
    import random

numpix = 24  # Number of NeoPixels
pixpin = board.D0  # Pin where NeoPixels are connected
strip = neopixel.NeoPixel(pixpin, numpix, brightness=0.3)

mode = 0  # Current animation effect
offset = 0  # Position of spinner animation
color = [255, 0, 0]  # RGB color - red
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
    elif mode == 1:  # Spinny wheels
        # A little trick here: pixels are processed in groups of 8
        # (with 2 of 8 on at a time), NeoPixel rings are 24 pixels
        # (8*3) and 16 pixels (8*2), so we can issue the same data
        # to both rings and it appears correct and contiguous
        # (also, the pixel order is different between the two ring
        # types, so we get the reversed motion on #2 for free).
        for i in range(numpix):  # For each LED...
            if ((offset + i) & 7) < 2:  # 2 pixels out of 8...
                strip[i] = color  # are set to current color
            else:
                strip[i] = [0, 0, 0]  # other pixels are off
        strip.write()  # Refresh LED states
        time.sleep(0.04)  # 40 millisecond delay
        offset += 1  # Shift animation by 1 pixel on next frame
        if offset >= 8:
            offset = 0
    # Additional animation modes could be added here!

    t = time.monotonic()  # Current time in seconds
    if (t - prevtime) >= 8:  # Every 8 seconds...
        mode += 1  # Advance to next mode
        if mode > 1:  # End of modes?
            mode = 0  # Start over from beginning
            # Rotate color R->G->B
            color = [color[2], color[0], color[1]]
        strip.fill([0, 0, 0])  # Turn off all pixels
        prevtime = t  # Record time of last mode change
