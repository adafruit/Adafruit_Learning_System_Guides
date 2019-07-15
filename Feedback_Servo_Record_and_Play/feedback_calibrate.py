# Example code for calibrating analog feedback values to servo range

import time
import board
import pulseio
from adafruit_motor import servo
from analogio import AnalogIn

# Pin setup
SERVO_PIN = board.A1
FEEDBACK_PIN = board.A5

# Calibration setup
ANGLE_MIN = 0
ANGLE_MAX = 180

# Setup servo
pwm = pulseio.PWMOut(SERVO_PIN, duty_cycle=2 ** 15, frequency=50)
servo = servo.Servo(pwm)
servo.angle = None

# Setup feedback
feedback = AnalogIn(FEEDBACK_PIN)

print("Servo feedback calibration.")
# Move to MIN angle
print("Moving to {}...".format(ANGLE_MIN), end="")
servo.angle = ANGLE_MIN
time.sleep(2)
print("Done.")
feedback_min = feedback.value
# Move to MAX angle
print("Moving to {}...".format(ANGLE_MAX), end="")
servo.angle = ANGLE_MAX
time.sleep(2)
print("Done.")
feedback_max = feedback.value
# Print results
print("Feedback MIN = {}".format(feedback_min))
print("Feedback MAX = {}".format(feedback_max))
# Deactivate servo
servo.angle = None
