# SPDX-FileCopyrightText: 2018 Anne Barela for Adafruit Industries
#
# SPDX-License-Identifier: MIT

# Code for the Trash Panda tutorial with Adafruit Crickit and Circuit Playground Express
import time
import board
from digitalio import DigitalInOut, Direction
from adafruit_crickit import crickit

# built in LED
led = DigitalInOut(board.D13)
led.direction = Direction.OUTPUT

# TowerPro servos like 500/2500 pulsewidths, make the wings flap a full 180
crickit.servo_1.set_pulse_width_range(min_pulse=500, max_pulse=2500)
crickit.servo_2.set_pulse_width_range(min_pulse=500, max_pulse=2500)

print("Its TRASH PANDA TIME!")

while True:
    print("tick")
    led.value = True
    crickit.servo_1.angle = 0
    time.sleep(0.5)
    crickit.servo_2.angle = 180
    time.sleep(1.0)

    print("tock")
    led.value = False
    crickit.servo_1.angle = 180
    time.sleep(0.5)
    crickit.servo_2.angle = 0
    time.sleep(1.0)
