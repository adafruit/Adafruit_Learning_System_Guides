# SPDX-FileCopyrightText: 2022 Liz Clark for Adafruit Industries
# SPDX-License-Identifier: MIT
"""
CircuitPython Capacitive Touch Pin Example for ESP32-S3.
Print to the serial console when one pin is touched.
"""
import time
import board
import touchio

touch = touchio.TouchIn(board.A2)

while True:
    if touch.value:
        print("Pin touched!")
    time.sleep(0.1)
