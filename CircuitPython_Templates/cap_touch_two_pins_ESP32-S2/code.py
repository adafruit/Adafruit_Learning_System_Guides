# SPDX-FileCopyrightText: 2021 Kattni Rembor for Adafruit Industries
# SPDX-License-Identifier: MIT
"""
CircuitPython Capacitive Two Touch Pin Example for ESP32-S2
Print to the serial console when a pin is touched.
"""
import time
import board
import touchio

touch_one = touchio.TouchIn(board.D8)
touch_two = touchio.TouchIn(board.D5)

while True:
    if touch_one.value:
        print("Pin one touched!")
    if touch_two.value:
        print("Pin two touched!")
    time.sleep(0.1)
