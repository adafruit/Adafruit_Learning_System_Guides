# SPDX-FileCopyrightText: 2023 Carter Nelson for Adafruit Industries
#
# SPDX-License-Identifier: MIT

# Example code for calibrating analog feedback values to servo range

import time
import board
import pwmio
from analogio import AnalogIn
from adafruit_motor import servo

# Pin setup
SERVO_PIN = board.A1
FEEDBACK_PIN = board.A3

# Calibration setup
ANGLE_MIN = 0
ANGLE_MAX = 180

# Setup servo
pwm = pwmio.PWMOut(SERVO_PIN, duty_cycle=2 ** 15, frequency=50)
servo = servo.Servo(pwm)
servo.angle = None

# Setup feedback
feedback = AnalogIn(FEEDBACK_PIN)

print("Servo feedback calibration.")

# Helper function to average analog readings
def read_feedback(samples=10, delay=0.01):
    reading = 0
    for _ in range(samples):
        reading += feedback.value
        time.sleep(delay)
    return int(reading/samples)

# Move to MIN angle
print("Moving to {}...".format(ANGLE_MIN), end="")
servo.angle = ANGLE_MIN
time.sleep(2)
print("Done.")
feedback_min = read_feedback()

# Move to MAX angle
print("Moving to {}...".format(ANGLE_MAX), end="")
servo.angle = ANGLE_MAX
time.sleep(2)
print("Done.")
feedback_max = read_feedback()

# Print results
print("="*20)
print("Feedback MIN = {}".format(feedback_min))
print("Feedback MAX = {}".format(feedback_max))
print("="*20)

# Deactivate servo
servo.angle = None
