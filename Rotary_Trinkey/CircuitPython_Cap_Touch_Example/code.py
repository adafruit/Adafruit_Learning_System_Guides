# SPDX-FileCopyrightText: 2021 Kattni Rembor for Adafruit Industries
#
# SPDX-License-Identifier: MIT

"""CircuitPython Capacitive Touch Example for Rotary Trinkey"""
import time
import board
import touchio

touch = touchio.TouchIn(board.TOUCH)

while True:
    if touch.value:
        print("Pad touched!")
    time.sleep(0.1)
