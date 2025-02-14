# SPDX-FileCopyrightText: 2023 Liz Clark for Adafruit Industries
#
# SPDX-License-Identifier: MIT

import time
import board
from digitalio import DigitalInOut, Direction, Pull

ir = DigitalInOut(board.D5)
ir.direction = Direction.INPUT
ir.pull = Pull.UP

while True:
    if not ir.value:
        print("object detected!")
    else:
        print("waiting for object...")
    time.sleep(0.01)
