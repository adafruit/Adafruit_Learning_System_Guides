# SPDX-FileCopyrightText: 2019 Phillip Burgess for Adafruit Industries
#
# SPDX-License-Identifier: MIT

# pylint: disable=import-error

"""
NeoPixel goggles inspired by Rezz

No interactive controls; speed, color and directions randomize periodically.
"""

from random import random, randrange
from time import monotonic
import board
import neopixel
import adafruit_fancyled.adafruit_fancyled as fancy

# Configurable defaults

BRIGHTNESS = 0.15  # 0.0 (off) to 1.0 (max brightness)

# Global variables

# Declare NeoPixel object. Data from ItsyBitsy pin 5 because it has built-in
# level shifting. Each LED eye has 44 pixels, so 88 total. Leave brightness
# at 1.0 here (NeoPixel library runs faster at full brightness) and adjust
# the global BRIGHTNESS above instead (used later when selecting HSV colors).
PIXELS = neopixel.NeoPixel(
    board.D5, 88, auto_write=False, brightness=1.0, pixel_order=neopixel.RGB)

# MODE indicates the current animation state through several bit fields.
# Bit 0 indicates the second eye is x-axis mirrored (1) or an exact copy
# of the first (0). Bit 1 indicates hue is slowly cycling (2) vs holding
# steady (0). Bit 2 indicates the middle of the 3 LED rings moves the
# opposite (4) or same (0) direction as the other 2.
MODE = randrange(8)  # 0 to 7
# Every few seconds, one of the above attributes is randomly toggled.
# This keeps track of the last time.
TIME_OF_LAST_MODE_SWITCH = 0
# HUE works around the color wheel, see FancyLED docs.
HUE = random()
# Relative position of MIDDLE of 3 rings, 0 to 143
MIDDLE_POS = randrange(144)
# Relative position of INNER and OUTER rings, 0 to 143
POS = randrange(144)
# Amount to increment POS and MIDDLE_POS each frame
SPEED = 2 + random() * 5

# The MIRROR_X and OFFSET(OUTER,MIDDLE,INNER) arrays precompute some values
# for each pixel so we don't need to repeat that math every frame or LED.
MIRROR_X = []
OFFSET_OUTER = []
OFFSET_MIDDLE = []
OFFSET_INNER = []
for i in range(24):
    MIRROR_X.append(67 - ((i + 11) % 24))
    OFFSET_OUTER.append(i * 6)
for i in range(16):
    MIRROR_X.append(83 - ((i + 7) % 16))
    OFFSET_MIDDLE.append(i * 9)
for i in range(4):
    MIRROR_X.append(87 - ((i + 2) % 4))
    OFFSET_INNER.append(i * 36)


def set_pixel(index, color):
    """Set one pixel in both eyes. Pass in pixel index (0 to 43) and
       color (as a packed RGB value). If MODE bit 0 is set, second eye
       will be X-axis mirrored, else an exact duplicate."""
    # Set pixel in first eye
    PIXELS[index] = color
    # Set pixel in second eye (mirrored or direct)
    if MODE & 1:
        PIXELS[MIRROR_X[index]] = color
    else:
        PIXELS[44 + index] = color


# Main loop, repeat indefinitely...
while True:

    # Check if 5 seconds have passed since last mode switch
    NOW = monotonic()
    if (NOW - TIME_OF_LAST_MODE_SWITCH) > 5:
        # Yes. Save the time, change ONE mode bit, randomize speed
        TIME_OF_LAST_MODE_SWITCH = NOW
        MODE ^= 1 << randrange(3)
        SPEED = 2 + random() * 5

    # Generate packed RGB value based on current HUE value
    COLOR = fancy.CHSV(HUE, 1.0, BRIGHTNESS).pack()

    # Draw outer ring; 24 pixels, 8 lit
    for i in range(24):
        j = (POS + OFFSET_OUTER[i]) % 72
        if j < 24:
            set_pixel(i, COLOR)
        else:
            set_pixel(i, 0)
    # Draw middle ring; 16 pixels, 6 lit
    for i in range(16):
        j = (OFFSET_MIDDLE[i] + MIDDLE_POS) % 72
        if j < 27:
            set_pixel(24 + i, COLOR)
        else:
            set_pixel(24 + i, 0)
    # Draw inner ring; 4 pixels, 3 lit
    for i in range(4):
        j = (POS + OFFSET_INNER[i]) % 144
        if j < 108:
            set_pixel(40 + i, COLOR)
        else:
            set_pixel(40 + i, 0)

    # Push new state to LEDs
    PIXELS.show()

    # If MODE bit 1 is set, advance hue (else holds steady)
    if MODE & 2:
        HUE += 0.003

    # Increment position of inner & outer ring
    POS = (POS + SPEED) % 144
    # Middle ring advances one way or other depending on MODE bit 2
    if MODE & 4:
        MIDDLE_POS = (MIDDLE_POS - SPEED) % 144
    else:
        MIDDLE_POS = (MIDDLE_POS + SPEED) % 144
