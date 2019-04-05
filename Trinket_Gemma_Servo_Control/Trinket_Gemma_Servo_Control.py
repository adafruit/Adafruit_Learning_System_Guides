# Trinket Gemma Servo Control
# for Adafruit M0 boards

import board
import pulseio
from adafruit_motor import servo
from analogio import AnalogIn

# servo pin for the M0 boards:
pwm = pulseio.PWMOut(board.A2, duty_cycle=2 ** 15, frequency=50)
my_servo = servo.Servo(pwm)
angle = 0

# potentiometer
trimpot = AnalogIn(board.A1)  # pot pin for servo control

def remap_range(value, left_min, left_max, right_min, right_max):
    # this remaps a value from original (left) range to new (right) range
    # Figure out how 'wide' each range is
    left_span = left_max - left_min
    right_span = right_max - right_min

    # Convert the left range into a 0-1 range (int)
    value_scaled = int(value - left_min) / int(left_span)

    # Convert the 0-1 range into a value in the right range.
    return int(right_min + (value_scaled * right_span))


while True:
    angle = remap_range(trimpot.value, 0, 65535, 0, 180)
    my_servo.angle = angle
