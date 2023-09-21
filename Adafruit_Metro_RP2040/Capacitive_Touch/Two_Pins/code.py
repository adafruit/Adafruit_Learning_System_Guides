# SPDX-FileCopyrightText: 2021 Kattni Rembor for Adafruit Industries
# SPDX-License-Identifier: MIT
"""
CircuitPython Capacitive Two Touch Pin Example - Print to the serial console when a pin is touched.
"""
import time
import board
import touchio

touch_one = touchio.TouchIn(board.A1)
touch_two = touchio.TouchIn(board.A2)

while True:
    if touch_one.value:
        print("Pin one touched!")
    if touch_two.value:
        print("Pin two touched!")
    time.sleep(0.1)
