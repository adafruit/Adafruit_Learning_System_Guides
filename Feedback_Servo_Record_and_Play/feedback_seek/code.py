# SPDX-FileCopyrightText: 2023 Carter Nelson for Adafruit Industries
#
# SPDX-License-Identifier: MIT

# Example code for using analog feedback value to seek a position
import time
import board
import pwmio
from analogio import AnalogIn
from simpleio import map_range
from adafruit_motor import servo

# Demo angles
angles = [0, 180, 0, 45, 180]

# Pin setup
SERVO_PIN = board.A1
FEEDBACK_PIN = board.A3

# Calibration setup
CALIB_MIN = 15377
CALIB_MAX = 42890
ANGLE_MIN = 0
ANGLE_MAX = 180

# Setup servo
pwm = pwmio.PWMOut(SERVO_PIN, duty_cycle=2 ** 15, frequency=50)
servo = servo.Servo(pwm)
servo.angle = None

# Setup feedback
feedback = AnalogIn(FEEDBACK_PIN)

def get_position():
    '''Turns analog feedback raw ADC value into angle.'''
    return map_range(feedback.value, CALIB_MIN, CALIB_MAX, ANGLE_MIN, ANGLE_MAX)

def seek_position(position, tolerance=2):
    '''Move to specified angle and wait until move is complete.'''
    servo.angle = position

    while abs(get_position() - position) > tolerance:
        pass

print("Servo feedback seek example.")
for angle in angles:
    print("Moving to {}...".format(angle), end="")
    start = time.monotonic()
    seek_position(angle)
    end = time.monotonic()
    print("Done. Move took {} seconds.".format(end-start))
    print("Pausing for 1 second.")
    time.sleep(1)

# Deactivate servo
print("Finished. Deactivating servo.")
servo.angle = None
