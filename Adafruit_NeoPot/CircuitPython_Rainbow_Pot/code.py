# SPDX-FileCopyrightText: 2025 Tim Cocks for Adafruit Industries
# SPDX-License-Identifier: MIT
"""
NeoPot NeoPixel Rainbow Demo
"""

import board
import analogio
import neopixel
import rainbowio

analog_pin = analogio.AnalogIn(board.A0)
knob_pixel = neopixel.NeoPixel(board.D4, 1, brightness=0.75, auto_write=True)

analog_smoothing_buffer = []


def map_range(x, in_min, in_max, out_min, out_max):
    return (x - in_min) / (in_max - in_min) * out_max - out_min


def average(values):
    if not values:
        return 0

    return sum(values) / len(values)


while True:
    analog_smoothing_buffer.insert(0, analog_pin.value)
    if len(analog_smoothing_buffer) >= 10:
        analog_smoothing_buffer.pop(-1)

    knob_pixel[0] = rainbowio.colorwheel(
        map_range(average(analog_smoothing_buffer), 0, 65525, 0, 255)
    )
