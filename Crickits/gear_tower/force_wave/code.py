# SPDX-FileCopyrightText: 2018 Limor Fried for Adafruit Industries
#
# SPDX-License-Identifier: MIT

import time
from busio import I2C
import analogio
from adafruit_seesaw.seesaw import Seesaw
from adafruit_seesaw.pwmout import PWMOut
from adafruit_motor import motor
import board

light = analogio.AnalogIn(board.LIGHT)

print("Wave on/off to turn")

# Create seesaw object
i2c = I2C(board.SCL, board.SDA)
seesaw = Seesaw(i2c)

# Create one motor on seesaw PWM pins 22 & 23
motor_a = motor.DCMotor(PWMOut(seesaw, 22), PWMOut(seesaw, 23))
motor_a.throttle = 0  # motor is stopped

while True:
    print((light.value,))
    # light value drops when a hand passes over
    if light.value < 4000:
        if motor_a.throttle:
            motor_a.throttle = 0
        else:
            motor_a.throttle = 1  # full speed forward

    while light.value < 5000:
        # wait till hand passes over completely
        pass
    time.sleep(0.1)
