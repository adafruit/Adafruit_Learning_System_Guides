# CircuitPython 3.0 CRICKIT dMake It Bubble
import time
from adafruit_crickit import crickit

motor_2 = crickit.dc_motor_2
motor_2.throttle = 1  # full speed forward

while True:
    print("servo up")
    crickit.servo_1.angle = 30
    time.sleep(2)
    print("servo down")
    crickit.servo_1.angle = 145
    time.sleep(0.4)
