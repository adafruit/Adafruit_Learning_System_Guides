# SPDX-FileCopyrightText: 2022 Liz Clark for Adafruit Industries
# SPDX-License-Identifier: MIT
"""CircuitPython Analog In Voltage Example for ESP32-S3"""
import time
import board
import analogio

analog_pin = analogio.AnalogIn(board.A0)


def get_voltage(pin):
    return (pin.value * 3.53) / 61285


while True:
    print(get_voltage(analog_pin))
    time.sleep(0.1)
