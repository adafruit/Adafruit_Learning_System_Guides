# SPDX-FileCopyrightText: 2017 Limor Fried for Adafruit Industries
#
# SPDX-License-Identifier: MIT

# CircuitPython IO demo #1 - General Purpose I/O

import time

import board
from digitalio import DigitalInOut, Direction, Pull

led = DigitalInOut(board.D13)
led.direction = Direction.OUTPUT

button = DigitalInOut(board.D2)
button.direction = Direction.INPUT
button.pull = Pull.UP

while True:
    # we could also just do "led.value = not button.value" !
    if button.value:
        led.value = False
    else:
        led.value = True

    time.sleep(0.01)  # debounce delay
