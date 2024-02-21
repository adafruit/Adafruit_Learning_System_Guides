# SPDX-FileCopyrightText: 2018 Anne Barela for Adafruit Industries
#
# SPDX-License-Identifier: MIT

import time

from adafruit_motor import servo
import board
import pwmio
from analogio import AnalogIn
from digitalio import DigitalInOut, Direction, Pull

pwm = pwmio.PWMOut(board.D5, frequency=50)

switch = DigitalInOut(board.D7)
switch.direction = Direction.INPUT
switch.pull = Pull.UP
pot = AnalogIn(board.A0)

continuous = servo.ContinuousServo(pwm)

def val(pin):
    # divides voltage (65535) to get a value between 0 and 1
    return pin.value / 65535

while True:

    if switch.value:
        continuous.throttle = val(pot) * -1
    else:
        continuous.throttle = val(pot) * 1

    time.sleep(0.001)
