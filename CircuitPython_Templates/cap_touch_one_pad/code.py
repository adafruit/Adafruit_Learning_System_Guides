# SPDX-FileCopyrightText: 2021 Kattni Rembor for Adafruit Industries
# SPDX-License-Identifier: Unlicense
"""
CircuitPython Capacitive Touch Pad Example - Print to the serial console when one pad is touched.

Update TOUCH_PAD_PIN to the touch pad pin name for the board you're using.

For example:
If you are using the BLM Badge, update TOUCH_PAD_PIN to CAP1.
If using a CPX, update TOUCH_PAD_PIN to A1.
"""
import time
import board
import touchio

touch = touchio.TouchIn(board.TOUCH_PAD_PIN)

while True:
    if touch.value:
        print("Pad touched!")
    time.sleep(0.1)
