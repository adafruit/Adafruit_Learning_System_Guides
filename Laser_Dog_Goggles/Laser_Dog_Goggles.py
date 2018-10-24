# Laser Dog Goggles
# https://learn.adafruit.com/laser-dog-goggles

import time
import board
import pulseio
from adafruit_motor import servo

# servo pin for the M0 boards:
pwm = pulseio.PWMOut(board.A2, duty_cycle=2 ** 15, frequency=50)
my_servo = servo.Servo(pwm)
speed = .04     # 40ms lower value means faster movement
max_turn = 180  # rotation range 180 degree, half a circle

while True:
    # move stepper max_turn degrees clockwise
    for angle in range(0, max_turn, 1):
        my_servo.angle = angle
        time.sleep(speed)

    # move stepper max_turn degrees counter clockwise
    for angle in range(max_turn, 0, -1):
        my_servo.angle = angle
        time.sleep(speed)
