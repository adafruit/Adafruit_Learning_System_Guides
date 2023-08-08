# SPDX-FileCopyrightText: 2021 Kattni Rembor for Adafruit Industries
# SPDX-License-Identifier: MIT
"""
CircuitPython Capacitive Touch Pin Example - Print to the serial console when one pin is touched.
"""
import time
import board
import touchio

touch = touchio.TouchIn(board.A1)

while True:
    if touch.value:
        print("Pin touched!")
    time.sleep(0.1)
