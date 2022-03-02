# SPDX-FileCopyrightText: 2018 Limor Fried for Adafruit Industries
#
# SPDX-License-Identifier: MIT

# CircuitPython 3.0 CRICKIT demo
import time
from digitalio import DigitalInOut, Direction, Pull
from adafruit_seesaw.seesaw import Seesaw
from adafruit_seesaw.pwmout import PWMOut
from adafruit_motor import servo, motor
from busio import I2C
import board

i2c = I2C(board.SCL, board.SDA)
ss = Seesaw(i2c)

print("Crickit demo!")

# use the CPX onboard switch to turn on/off (helps calibrate)
switch = DigitalInOut(board.SLIDE_SWITCH)
switch.direction = Direction.INPUT
switch.pull = Pull.UP

#################### 4 Servos
servos = []
for ss_pin in (17, 16, 15, 14):
    pwm = PWMOut(ss, ss_pin)
    pwm.frequency = 50
    _servo = servo.Servo(pwm)
    _servo.angle = 90   # starting angle, middle
    servos.append(_servo)

#################### 2 DC motors
motors = []
for ss_pin in ((22, 23), (18, 19)):
    pwm0 = PWMOut(ss, ss_pin[0])
    pwm1 = PWMOut(ss, ss_pin[1])
    _motor = motor.DCMotor(pwm0, pwm1)
    motors.append(_motor)

servos[0].angle = 180

while True:
    if switch.value:
        # Switch is on, activate MUSIC POWER!

        # motor forward slowly
        motors[0].throttle = 0.2
        # mote the head forward slowly, over 0.9 seconds
        for a in range(180, 90, -1):
            servos[0].angle = a
            time.sleep(0.01)

        # motor stop
        motors[0].throttle = 0
        time.sleep(1)

        # motor backwards slowly
        motors[0].throttle = -0.2
        # move the head back slowly too, over 0.9 seconds
        for a in range(90, 180):
            servos[0].angle = a
            time.sleep(0.01)
        # calibration! its a *tiny* bit slower going back so give it a few ms
        time.sleep(0.007)

        # motor stop
        motors[0].throttle = 0
        time.sleep(1)
    else:
        # switch is 'off' so dont do anything!
        pass
