# SPDX-FileCopyrightText: 2021 Kattni Rembor for Adafruit Industries
#
# SPDX-License-Identifier: MIT

"""
CircuitPython Capacitive Two Touch Pad Example - Print to the serial console when a pad is touched.
"""
import time
import board
import touchio

touch_one = touchio.TouchIn(board.TOUCH1)
touch_two = touchio.TouchIn(board.TOUCH2)

while True:
    if touch_one.value:
        print("Pad one touched!")
    if touch_two.value:
        print("Pad two touched!")
    time.sleep(0.1)
