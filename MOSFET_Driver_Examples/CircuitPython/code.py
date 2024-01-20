# SPDX-FileCopyrightText: 2022 Liz Clark for Adafruit Industries
#
# SPDX-License-Identifier: MIT

import time
import board
from digitalio import DigitalInOut, Direction

# motor output
solenoid = DigitalInOut(board.D5)
solenoid.direction = Direction.OUTPUT

while True:
    solenoid.value = False
    print("The motor is not triggered.")
    time.sleep(1)
    solenoid.value = True
    print("The motor is triggered.")
    time.sleep(1)
