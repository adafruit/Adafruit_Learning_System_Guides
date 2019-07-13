# Example code for using analog feedback value to seek a position
import board
import pulseio
from simpleio import map_range
from adafruit_motor import servo
from analogio import AnalogIn

# Demo angles
angles = [0, 180, 0, 45, 180]

# Pin setup
SERVO_PIN = board.A1
FEEDBACK_PIN = board.A5

# Calibration setup
CALIB_MIN = 18112
CALIB_MAX = 49408
ANGLE_MIN = 0
ANGLE_MAX = 180

# Setup servo
pwm = pulseio.PWMOut(SERVO_PIN, duty_cycle=2 ** 15, frequency=50)
servo = servo.Servo(pwm)
servo.angle = None

# Setup feedback
feedback = AnalogIn(FEEDBACK_PIN)

def get_position():
    return map_range(feedback.value, CALIB_MIN, CALIB_MAX, ANGLE_MIN, ANGLE_MAX)

def seek_position(position, tolerance=2):
    servo.angle = position

    while abs(get_position() - position) > tolerance:
        pass

print("Servo feedback seek example.")
for angle in angles:
    print("Moving to {}...".format(angle), end="")
    seek_position(angle)
    print("Done.")
