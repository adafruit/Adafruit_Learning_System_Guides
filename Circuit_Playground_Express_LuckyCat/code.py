# Lucky Cat Maneki-neko with Circuit Playground Express
# Mike Barela for Adafruit Industries, MIT License

import time
import board
import pulseio
from adafruit_motor import servo
 
# create a PWMOut object on Pin A1.
pwm = pulseio.PWMOut(board.A1, duty_cycle=2 ** 15, frequency=50)
 
# Create a servo object, my_servo
my_servo = servo.Servo(pwm)

while True:
    for angle in range(50):  # 0 to 49 degrees in 1 deg steps
        my_servo.angle = angle
        time.sleep(0.0045)   # Tiny delay each steps
    time.sleep(0.25)        # More time at end of arm down
    for angle in range(50):  # 49 to 0 degrees in 1 deg steps
        my_servo.angle = 49 - angle
        time.sleep(0.0045)
    time.sleep(0.25)        # More time when arm up
