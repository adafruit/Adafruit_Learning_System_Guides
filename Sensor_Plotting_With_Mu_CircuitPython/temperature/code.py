# SPDX-FileCopyrightText: 2018 Kattni Rembor for Adafruit Industries
#
# SPDX-License-Identifier: MIT

import time

import adafruit_thermistor
import board

thermistor = adafruit_thermistor.Thermistor(
    board.TEMPERATURE, 10000, 10000, 25, 3950)

while True:
    print((thermistor.temperature,))
    # print(((thermistor.temperature * 9 / 5 + 32),))  # Fahrenheit
    time.sleep(0.25)
