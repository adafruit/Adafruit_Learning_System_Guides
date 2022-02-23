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


print("Theramin-like turning")

# Create seesaw object
i2c = I2C(board.SCL, board.SDA)
seesaw = Seesaw(i2c)

# Create one motor on seesaw PWM pins 22 & 23
motor_a = motor.DCMotor(PWMOut(seesaw, 22), PWMOut(seesaw, 23))
motor_a.throttle = 0 # motor is stopped

def map_range(x, in_min, in_max, out_min, out_max):
    # Maps a number from one range to another.
    mapped = (x-in_min) * (out_max - out_min) / (in_max-in_min) + out_min
    if out_min <= out_max:
        return max(min(mapped, out_max), out_min)
    return min(max(mapped, out_max), out_min)

while True:
    print((light.value,))
    motor_a.throttle = map_range(light.value, 500, 8000, 1.0, 0)
    time.sleep(0.1)
