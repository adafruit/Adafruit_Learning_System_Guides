# Trinket Gemma Servo Control
# for Adafruit M0 boards

import board
import pulseio
from adafruit_motor import servo

# servo pin for the M0 boards:
pwm = pulseio.PWMOut(board.A2, duty_cycle=2 ** 15, frequency=50)
my_servo = servo.Servo(pwm)

while True:
    for angle in range(0,100,5)
        print(angle)
        my_servo.angle = angle

    for angle in range(100,0,-5)
        print(angle)
        my_servo.angle = angle
