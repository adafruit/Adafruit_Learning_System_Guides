# SPDX-FileCopyrightText: 2021 Kattni Rembor for Adafruit Industries
# SPDX-License-Identifier: Unlicense
"""CircuitPython analog pin value example"""
import time
import board
import analogio

analog_pin = analogio.AnalogIn(board.A0)

while True:
    print(analog_pin.value)
    time.sleep(0.1)
