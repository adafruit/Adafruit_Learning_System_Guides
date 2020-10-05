"""
This example script shows how to sweep servo(s) without using
time.sleep().
"""

import board
import digitalio
import time
import pulseio
from adafruit_motor import servo

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
    pwm = pulseio.PWMOut(cur_servo["PIN"], duty_cycle=2 ** 15, frequency=50)
    # Create a servo object.
    cur_servo["SERVO"] = servo.Servo(pwm)


while True:
    # Store the current time to refer to later.
    now = time.monotonic()
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
