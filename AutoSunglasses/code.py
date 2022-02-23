# SPDX-FileCopyrightText: 2018 Dave Astels for Adafruit Industries
#
# SPDX-License-Identifier: MIT

"""
Circuit Playground Express auto-sunglasses/flashlight

Adafruit invests time and resources providing this open source code.
Please support Adafruit and open source hardware by purchasing
products from Adafruit!

Written by Dave Astels for Adafruit Industries
Copyright (c) 2018 Adafruit Industries
Licensed under the MIT license.

All text above must be included in any redistribution.
"""

import time
import board
import pwmio
from adafruit_circuitplayground.express import cpx
from adafruit_motor import servo

pwm = pwmio.PWMOut(board.A1, duty_cycle=2 ** 15, frequency=50)
my_servo = servo.Servo(pwm)

cpx.pixels.fill((0, 0, 0))
my_servo.angle = 90

while True:
    light_level = cpx.light

    if light_level < 10:
        cpx.pixels.fill((200, 200, 200))
    else:
        cpx.pixels.fill((0, 0, 0))
        if light_level < 200:
            my_servo.angle = 90
        else:
            my_servo.angle = 0

    time.sleep(0.25)
