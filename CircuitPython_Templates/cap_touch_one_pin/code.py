# SPDX-FileCopyrightText: 2021 Kattni Rembor for Adafruit Industries
# SPDX-License-Identifier: MIT
"""
CircuitPython Capacitive Touch Pin Example - Print to the serial console when one pin is touched.

Update TOUCH_PIN to the touch-capable pin name for the board you're using.

For example:
If you are using A0 on the Feather RP2040, update TOUCH_PIN to A0.
"""
import time
import board
import touchio

touch = touchio.TouchIn(board.TOUCH_PIN)

while True:
    if touch.value:
        print("Pin touched!")
    time.sleep(0.1)
