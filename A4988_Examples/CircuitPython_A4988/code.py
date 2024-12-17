# SPDX-FileCopyrightText: 2024 Liz Clark for Adafruit Industries
#
# SPDX-License-Identifier: MIT

import time
import board
from digitalio import DigitalInOut, Direction

# direction and step pins as outputs
DIR = DigitalInOut(board.D5)
DIR.direction = Direction.OUTPUT
STEP = DigitalInOut(board.D6)
STEP.direction = Direction.OUTPUT

# microstep mode, default is 1/16 so 16
# another ex: 1/4 microstep would be 4
microMode = 16
# full rotation multiplied by the microstep divider
steps = 200 * microMode

while True:
    # change direction every loop
    DIR.value = not DIR.value
    # toggle STEP pin to move the motor
    for i in range(steps):
        STEP.value = True
        time.sleep(0.001)
        STEP.value = False
        time.sleep(0.001)
    print("rotated! now reverse")
    # 1 second delay before starting again
    time.sleep(1)
