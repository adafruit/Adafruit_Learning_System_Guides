"""
Fluttering Fairy Wings
Adafruit invests time and resources providing this open source code.
Please support Adafruit and open source hardware by purchasing
products from Adafruit!
Written by Erin St Blaine for Adafruit Industries
Copyright (c) 2020-2021 Adafruit Industries
Licensed under the MIT license.
All text above must be included in any redistribution.
"""

import time
import random
import board
from analogio import AnalogIn
from adafruit_servokit import ServoKit

analog_in = AnalogIn(board.A0)
kit = ServoKit(channels=8)

SERVO_MIN = 0
SERVO_MAX = 130
DELAY_MIN = 0.01  # In seconds, is the longest DELAY between servo moves
DELAY_MAX = 0.1   # In seconds, is the longest DELAY between servo moves

DELAY = DELAY_MAX

def set_delay():
    '''calibrate to potentiometer'''
    global DELAY # pylint: disable=global-statement
    DELAY = DELAY_MIN + DELAY_MAX * (65535 - analog_in.value) / 65535
    #print(DELAY\

while True:
    num_flaps = random.randint(1, 4)

    print("Flapping", num_flaps, "times")
    for flap in range(num_flaps):
        print("Open")
        set_delay()
        for angle in range(SERVO_MIN, SERVO_MAX, 2): # move 2 deg at a time
            kit.servo[0].angle = angle
            kit.servo[1].angle = SERVO_MAX-angle
            time.sleep(DELAY)
        print("Close")
        set_delay()
        for angle in range(SERVO_MIN, SERVO_MAX, 2): # move 2 deg at a time
            kit.servo[0].angle = SERVO_MAX-angle
            kit.servo[1].angle = angle
            time.sleep(DELAY*2)
    print("Waiting...")
    time.sleep(random.randint(2, 10))  # wait 2 to 10 seconds
