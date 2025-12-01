# SPDX-FileCopyrightText: 2017 Phillip Burgess for Adafruit Industries
#
# SPDX-License-Identifier: MIT

# NeoPixel earrings example.  Makes a nice blinky display with just a
# few LEDs on at any time...uses MUCH less juice than rainbow display!

import time
from rainbowio import colorwheel
import board
import neopixel
import adafruit_dotstar

try:
    import urandom as random  # for v1.0 API support
except ImportError:
    import random

dot = adafruit_dotstar.DotStar(board.APA102_SCK, board.APA102_MOSI, 1, brightness=0.2)
dot[0] = (0, 0, 0)

numpix = 16  # Number of NeoPixels (e.g. 16-pixel ring)
pixpin = board.D0  # Pin where NeoPixels are connected
strip = neopixel.NeoPixel(pixpin, numpix, brightness=.3, auto_write=False)

mode = 0  # Current animation effect
offset = 0  # Position of spinner animation
hue = 0  # Starting hue
color = colorwheel(hue & 255)  # hue -> RGB color
prevtime = time.monotonic()  # Time of last animation mode switch

while True:  # Loop forever...
    if mode == 0:  # Random sparkles - lights just one LED at a time
        i = random.randint(0, numpix - 1)  # Choose random pixel
        strip[i] = color   # Set it to current color
        strip.show()       # Refresh LED states
        # Set same pixel to "off" color now but DON'T refresh...
        # it stays on for now...bot this and the next random
        # pixel will be refreshed on the next pass.
        strip[i] = [0, 0, 0]
        time.sleep(0.008)  # 8 millisecond delay
    elif mode == 1:  # Spinny colorwheel (4 LEDs on at a time)
        for i in range(numpix):  # For each LED...
            if ((offset + i) & 7) < 2:  # 2 pixels out of 8...
                strip[i] = color    # are set to current color
            else:
                strip[i] = [0, 0, 0]  # other pixels are off
        strip.show()     # Refresh LED states
        time.sleep(0.04) # 40 millisecond delay
        offset += 1      # Shift animation by 1 pixel on next frame
        if offset >= 8:
            offset = 0
    # Additional animation modes could be added here!

    t = time.monotonic()  # Current time in seconds
    if (t - prevtime) >= 8:  # Every 8 seconds...
        mode += 1  # Advance to next mode
        if mode > 1:  # End of modes?
            mode = 0  # Start over from beginning
            hue += 80  # And change color
            color = colorwheel(hue & 255)
        strip.fill([0, 0, 0])  # Turn off all pixels
        prevtime = t  # Record time of last mode change
