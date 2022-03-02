# SPDX-FileCopyrightText: 2018 Anne Barela for Adafruit Industries
#
# SPDX-License-Identifier: MIT

import time
from adafruit_crickit import crickit

# Create one motor on seesaw motor port #1
motor = crickit.dc_motor_1
motor.throttle = 0.5  # half speed forward

# Create drive (PWM) object for the lights on Drive 1
lights = crickit.drive_1
lights.frequency = 1000 # Our default frequency is 1KHz

while True:
    lights.fraction = 0.5  # half on
    time.sleep(0.8)

    lights.fraction = 0.2  # dim
    time.sleep(0.1)

    # and repeat!
