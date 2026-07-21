# SPDX-FileCopyrightText: 2026 Erin St Blaine
# SPDX-License-Identifier: MIT

"""Light all the dress NeoPixels yellow for testing."""

import time
import board
import digitalio
import neopixel


NUM_PIXELS = 216
BRIGHTNESS = 0.2
YELLOW = (255, 255, 0)


# Turn on the board's external NeoPixel power.
external_power = digitalio.DigitalInOut(board.EXTERNAL_POWER)
external_power.direction = digitalio.Direction.OUTPUT
external_power.value = True


# Set up the dress NeoPixels.
pixels = neopixel.NeoPixel(
    board.EXTERNAL_NEOPIXELS,
    NUM_PIXELS,
    brightness=BRIGHTNESS,
    auto_write=False,
    pixel_order=neopixel.BGR,
)


# Light every pixel yellow.
pixels.fill(YELLOW)
pixels.show()


# Keep the program running.
while True:
    time.sleep(1)
