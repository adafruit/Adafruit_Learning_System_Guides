# SPDX-FileCopyrightText: 2026 Erin St Blaine for Adafruit Industries
#
# SPDX-License-Identifier: MIT

"""Simple three-spoke DotStar color test."""

import time
import board
import digitalio

NUM_PIXELS = 36

CLOCK_PIN = board.SCK
DATA_PINS = (board.A1, board.A2, board.A3)

COLORS = (
    (255, 0, 0),  # Red
    (0, 255, 0),  # Green
    (0, 0, 255),  # Blue
)


def write_dotstar(data_pin, color):
    """Fill one DotStar strip with a solid color."""
    data = digitalio.DigitalInOut(data_pin)
    clock = digitalio.DigitalInOut(CLOCK_PIN)

    data.direction = digitalio.Direction.OUTPUT
    clock.direction = digitalio.Direction.OUTPUT

    data.value = False
    clock.value = False

    def send_byte(value):
        """Send one byte of data to the DotStar strip."""
        for bit in range(7, -1, -1):
            data.value = bool(value & (1 << bit))
            clock.value = True
            clock.value = False

    # DotStar start frame
    for _ in range(4):
        send_byte(0x00)

    red, green, blue = color

    # Pixel data
    for _ in range(NUM_PIXELS):
        send_byte(0xFF)
        send_byte(blue)
        send_byte(green)
        send_byte(red)

    # DotStar end frame
    for _ in range(4):
        send_byte(0xFF)

    data.deinit()
    clock.deinit()


while True:
    for strip_pin, strip_color in zip(DATA_PINS, COLORS):
        write_dotstar(strip_pin, strip_color)

    time.sleep(1)
