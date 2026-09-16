# SPDX-FileCopyrightText: 2026 Erin St Blaine for Adafruit Industries
#
# SPDX-License-Identifier: MIT

"""Simple three-spoke DotStar color test using the adafruit_dotstar library."""

import time

import adafruit_dotstar
import board

NUM_PIXELS = 36

CLOCK_PIN = board.SCK
DATA_PINS = (board.A1, board.A2, board.A3)

COLORS = (
    (255, 0, 0),  # Red
    (0, 255, 0),  # Green
    (0, 0, 255),  # Blue
)


class SpokeDotStar(adafruit_dotstar.DotStar):
    """DotStar strip that keeps its pixels lit when its pins are released.

    All three spokes share one clock pin, so only one strip can own the pins
    at a time. The stock ``deinit`` blanks the strip before releasing the
    pins; this version releases them and leaves the last colors showing.
    """

    def deinit(self) -> None:
        if self._spi:
            self._spi.deinit()
        else:
            self.dpin.deinit()
            self.cpin.deinit()


def write_dotstar(data_pin, color):
    """Fill one DotStar strip with a solid color."""
    with SpokeDotStar(CLOCK_PIN, data_pin, NUM_PIXELS) as strip:
        strip.fill(color)


while True:
    for strip_pin, strip_color in zip(DATA_PINS, COLORS):
        write_dotstar(strip_pin, strip_color)

    time.sleep(1)
