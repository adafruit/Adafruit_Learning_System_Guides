# SPDX-FileCopyrightText: 2020 FoamyGuy for Adafruit Industries
#
# SPDX-License-Identifier: MIT

"""
This example script shows the usage of servos, and LEDs
used simultaneously without interrupting each other.
"""

import time
import board
import digitalio
import neopixel
import pwmio
from adafruit_motor import servo

pixels = neopixel.NeoPixel(board.NEOPIXEL, 1)
pixels[0] = (0, 0, 0)

BLINK_LIST = [
    {
        "ON": 0.25,
        "OFF": 0.25,
        "PREV_TIME": -1,
        "PIN": board.D5,
    },
    {
        "ON": 0.5,
        "OFF": 0.5,
        "PREV_TIME": -1,
        "PIN": board.D6,
    },
    {
        "ON": 1.0,
        "OFF": 1.0,
        "PREV_TIME": -1,
        "PIN": board.D9,
    },
    {
        "ON": 2.0,
        "OFF": 2.0,
        "PREV_TIME": -1,
        "PIN": board.D10,
    }
]

SERVO_LIST = [
    {
        "MAX_ANGLE": 180,
        "MIN_ANGLE": 0,
        "PREV_TIME": -1,
        "PIN": board.A1,
        "DELAY_BETWEEN": 0.05,
        "SERVO": None,
        "MOVE_BY": 5
    }
]

for cur_servo in SERVO_LIST:
    pwm = pwmio.PWMOut(cur_servo["PIN"], duty_cycle=2 ** 15, frequency=50)
    # Create a servo object.
    cur_servo["SERVO"] = servo.Servo(pwm)


for led in BLINK_LIST:
    led["PIN"] = digitalio.DigitalInOut(led["PIN"])
    led["PIN"].direction = digitalio.Direction.OUTPUT

while True:
    # Store the current time to refer to later.
    now = time.monotonic()

    for led in BLINK_LIST:
        if led["PIN"].value is False:
            if now >= led["PREV_TIME"] + led["OFF"]:
                led["PREV_TIME"] = now
                led["PIN"].value = True
        if led["PIN"].value is True:
            if now >= led["PREV_TIME"] + led["ON"]:
                led["PREV_TIME"] = now
                led["PIN"].value = False

    for servo in SERVO_LIST:
        if now >= servo["PREV_TIME"] + servo["DELAY_BETWEEN"]:
            try:
                servo["SERVO"].angle += servo["MOVE_BY"]
            except ValueError as e:

                if servo["MOVE_BY"] > 0:
                    servo["SERVO"].angle = servo["MAX_ANGLE"]
                else:
                    servo["SERVO"].angle = servo["MIN_ANGLE"]


            if servo["SERVO"].angle >= servo["MAX_ANGLE"] or \
                servo["SERVO"].angle <= servo["MIN_ANGLE"]:

                servo["MOVE_BY"] = -servo["MOVE_BY"]

            servo["PREV_TIME"] = now
