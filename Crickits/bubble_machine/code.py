# CircuitPython 3.0 CRICKIT demo
import time

import board
from adafruit_motor import servo, motor
from adafruit_seesaw.pwmout import PWMOut
from adafruit_seesaw.seesaw import Seesaw
from busio import I2C

i2c = I2C(board.SCL, board.SDA)
ss = Seesaw(i2c)

print("Bubble machine!")

SERVOS = True
DCMOTORS = True

# Create 4 Servos
servos = []
if SERVOS:
    for ss_pin in (17, 16, 15, 14):
        pwm = PWMOut(ss, ss_pin)
        pwm.frequency = 50
        _servo = servo.Servo(pwm)
        _servo.angle = 90  # starting angle, middle
        servos.append(_servo)

# Create 2 DC motors
motors = []
if DCMOTORS:
    for ss_pin in ((18, 19), (22, 23)):
        pwm0 = PWMOut(ss, ss_pin[0])
        pwm1 = PWMOut(ss, ss_pin[1])
        _motor = motor.DCMotor(pwm0, pwm1)
        motors.append(_motor)

while True:
    print("servo down")
    servos[0].angle = 180
    time.sleep(1)
    print("fan on")
    motors[0].throttle = 1
    time.sleep(3)
    print("fan off")
    time.sleep(1)
    motors[0].throttle = 0
    print("servo up")
    servos[0].angle = 0
    time.sleep(1)
