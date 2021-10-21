# SPDX-FileCopyrightText: 2021 Phil Burgess for Adafruit Industries
#
# SPDX-License-Identifier: MIT

"""
EyeLightsAnim example for Adafruit EyeLights (LED Glasses + Driver).
The accompanying eyelights_anim.py provides pre-drawn frame-by-frame
animation from BMP images. Sort of a catch-all for modest projects that may
want to implement some animation without having to express that animation
entirely in code. The idea is based upon two prior projects:

https://learn.adafruit.com/32x32-square-pixel-display/overview
learn.adafruit.com/circuit-playground-neoanim-using-bitmaps-to-animate-neopixels

The 18x5 matrix and the LED rings are regarded as distinct things, fed from
two separate BMPs (or can use just one or the other). The former guide above
uses the vertical axis for time (like a strip of movie film), while the
latter uses the horizontal axis for time (as in audio or video editing).
Despite this contrast, the same conventions are maintained here to avoid
conflicting explanations...what worked in those guides is what works here,
only the resolutions are different. See also the example BMPs.
"""

import time
import board
from busio import I2C
import adafruit_is31fl3741
from adafruit_is31fl3741.adafruit_ledglasses import LED_Glasses
from eyelights_anim import EyeLightsAnim


# HARDWARE SETUP -----------------------

i2c = I2C(board.SCL, board.SDA, frequency=1000000)

# Initialize the IS31 LED driver, buffered for smoother animation
glasses = LED_Glasses(i2c, allocate=adafruit_is31fl3741.MUST_BUFFER)
glasses.show()  # Clear any residue on startup
glasses.global_current = 20  # Just middlin' bright, please


# ANIMATION SETUP ----------------------

# Two indexed-color BMP filenames are specified: first is for the LED matrix
# portion, second is for the LED rings -- or pass None for one or the other
# if not animating that part. The two elements, matrix and rings, share a
# few LEDs in common...by default the rings appear "on top" of the matrix,
# or you can optionally pass a third argument of False to have the rings
# underneath. There's that one odd unaligned pixel between the two though,
# so this may only rarely be desirable.
anim = EyeLightsAnim(glasses, "matrix.bmp", "rings.bmp")


# MAIN LOOP ----------------------------

# This example just runs through a repeating cycle. If you need something
# else, like ping-pong animation, or frames based on a specific time, the
# anim.frame() function can optionally accept two arguments: an index for
# the matrix animation, and an index for the rings.

while True:
    anim.frame()  #     Advance matrix and rings by 1 frame and wrap around
    glasses.show()  #   Update LED matrix
    time.sleep(0.02)  # Pause briefly
