# SPDX-FileCopyrightText: 2024 ladyada for Adafruit Industries
#
# SPDX-License-Identifier: MIT

import time
import board
from analogio import AnalogIn
from digitalio import DigitalInOut, Direction

led = DigitalInOut(board.LED)
led.direction = Direction.OUTPUT

analog_in = AnalogIn(board.A3)

def get_vsys(pin):
    return ((pin.value * 3) * 3.3) / 65536

while True:
    led.value = True
    print(f"The battery level is: {get_vsys(analog_in):.1f}V")
    led.value = False
    time.sleep(5)
