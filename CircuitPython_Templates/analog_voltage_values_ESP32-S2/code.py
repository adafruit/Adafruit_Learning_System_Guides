# SPDX-FileCopyrightText: 2022 Kattni Rembor for Adafruit Industries
# SPDX-License-Identifier: MIT
"""CircuitPython Analog In Voltage Example for ESP32-S2"""
import time
import board
import analogio

analog_pin = analogio.AnalogIn(board.A0)


def get_voltage(pin):
    return (pin.value * 2.57) / 51000


while True:
    print(get_voltage(analog_pin))
    time.sleep(0.1)
