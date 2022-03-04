# SPDX-FileCopyrightText: 2021 Kattni Rembor for Adafruit Industries
# SPDX-License-Identifier: MIT
"""
CircuitPython analog voltage value example

REMOVE THIS TEXT AND ALL THE FOLLOWING, AND THE PYLINT DISABLE COMMENT, BEFORE SUBMITTING TO LEARN:
Update VOLTAGE to the max voltage returned by the board you're using.
Update VALUE to the max analog pin value returned by the board you're using.

For example:
If you are using Feather ESP32-S2, update VOLTAGE to 2.6 and VALUE to 51375.

Remove the #pylint: disable=undefined-variable before submitting to Learn. It is unnecessary
once the VOLTAGE and VALUE are updated to valid numbers.
"""
import time
import board
import analogio

analog_pin = analogio.AnalogIn(board.A0)


def get_voltage(pin):
    return (pin.value * VOLTAGE) / VALUE  # pylint: disable=undefined-variable


while True:
    print(get_voltage(analog_pin))
    time.sleep(0.1)
