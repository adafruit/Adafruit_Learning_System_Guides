# SPDX-FileCopyrightText: 2026 Erin St Blaine
# SPDX-License-Identifier: MIT

"""Light each NeoPixel individually to identify its position."""

# CircuitPython hardware modules are provided on-device, not by desktop Python.
# pylint: disable=import-error

import time
import board
import digitalio
import neopixel


NUM_PIXELS = 216
BRIGHTNESS = 0.3

# Time each pixel remains illuminated.
PIXEL_DELAY = 4.0

# Pause before starting the sequence again.
REPEAT_DELAY = 10.0

TEST_COLOR = (255, 255, 255)

EXTERNAL_POWER = digitalio.DigitalInOut(board.EXTERNAL_POWER)
EXTERNAL_POWER.direction = digitalio.Direction.OUTPUT
EXTERNAL_POWER.value = True

PIXELS = neopixel.NeoPixel(
    board.EXTERNAL_NEOPIXELS,
    NUM_PIXELS,
    brightness=BRIGHTNESS,
    auto_write=False,
    pixel_order=neopixel.BGR,
)


def identify_pixels():
    """Light and print each pixel number, one at a time."""
    while True:
        for pixel_index in range(NUM_PIXELS):
            PIXELS.fill((0, 0, 0))
            PIXELS[pixel_index] = TEST_COLOR
            PIXELS.show()

            print("Pixel:", pixel_index)
            time.sleep(PIXEL_DELAY)

        PIXELS.fill((0, 0, 0))
        PIXELS.show()

        print("Sequence complete. Restarting soon.")
        time.sleep(REPEAT_DELAY)


identify_pixels()
