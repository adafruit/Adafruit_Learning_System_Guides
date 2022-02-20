# SPDX-FileCopyrightText: 2018 Dan Halbert for Adafruit Industries
#
# SPDX-License-Identifier: MIT

import time

import board
import touchio
import adafruit_dotstar

# Red, green, blue, and simple mixes of 2 or 3.
# Add your own choices here.
COLORS = (
    (0, 255, 0),
    (0, 0, 255),
    (255, 0, 0),
    (0, 255, 255),
    (255, 255, 0),
    (255, 0, 255),
    (255, 255, 255),
)

# The two left touch pads adjust the brightness.
# The right touch pad changes colors.
# Hold down or just tap.
brightness_down = touchio.TouchIn(board.D0)
brightness_up = touchio.TouchIn(board.D2)
change_color = touchio.TouchIn(board.D1)

dotstar = adafruit_dotstar.DotStar(board.APA102_SCK, board.APA102_MOSI, 1)
BRIGHTNESS_STEPS = 15
# Start at medium brightness, green.
brightness_step = 8
color_index = 0

while True:
    if brightness_down.value:
        # Don't go below 1.
        brightness_step = max(1, brightness_step - 1)

    if brightness_up.value:
        # Don't go above BRIGHTNESS_STEPS.
        brightness_step = min(BRIGHTNESS_STEPS, brightness_step + 1)

    if change_color.value:
        # Cycle through 0 to len(COLORS)-1 and then wrap around.
        color_index = (color_index + 1) % len(COLORS)

    # Scale brightness to be 0.0 - 1.0.
    dotstar.brightness = brightness_step / BRIGHTNESS_STEPS
    dotstar.fill(COLORS[color_index])

    time.sleep(0.2)
