# SPDX-FileCopyrightText: 2021 Kattni Rembor for Adafruit Industries
#
# SPDX-License-Identifier: MIT

import time
import board
from analogio import AnalogIn
import adafruit_simplemath

analog_in = AnalogIn(board.POTENTIOMETER)


def read_pot(samples, min_val, max_val):
    sum_samples = 0
    for _ in range(samples):
        sum_samples += analog_in.value
    sum_samples /= samples  # ok take the average

    return adafruit_simplemath.map_range(sum_samples, 100, 65535, min_val, max_val)


while True:
    print("Slider:", round(read_pot(10, 0, 100)))
    time.sleep(0.1)
