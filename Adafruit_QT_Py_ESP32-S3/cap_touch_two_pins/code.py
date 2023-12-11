# SPDX-FileCopyrightText: 2022 Liz Clark for Adafruit Industries
# SPDX-License-Identifier: MIT
"""
CircuitPython Capacitive Two Touch Pin Example for ESP32-S3
Print to the serial console when a pin is touched.
"""
import time
import board
import touchio

touch_one = touchio.TouchIn(board.A2)
touch_two = touchio.TouchIn(board.TX)

while True:
    if touch_one.value:
        print("Pin one touched!")
    if touch_two.value:
        print("Pin two touched!")
    time.sleep(0.1)
