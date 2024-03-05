# SPDX-FileCopyrightText: 2024 Liz Clark for Adafruit Industries
# SPDX-License-Identifier: MIT

import time
import board
from digitalio import DigitalInOut, Direction
from analogio import AnalogIn

analog_in = AnalogIn(board.A1)

switch = DigitalInOut(board.D5)
switch.direction = Direction.OUTPUT

switch_time = 2
clock = time.monotonic()
while True:
    if (time.monotonic() - clock) > switch_time:
        switch.value = not switch.value
        print(switch.value)
        clock = time.monotonic()
    print((analog_in.value,))
    time.sleep(0.1)
