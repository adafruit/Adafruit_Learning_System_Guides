# SPDX-FileCopyrightText: 2021 Kattni Rembor for Adafruit Industries
# SPDX-License-Identifier: MIT
"""CircuitPython analog pin value example"""
import time
import board
import analogio

analog_pin = analogio.AnalogIn(board.D3)

while True:
    print(analog_pin.value)
    time.sleep(0.1)
