# SPDX-FileCopyrightText: 2021 jedgarpark for Adafruit Industries
# SPDX-License-Identifier: MIT

# Pico motor party demo board
# Hardware setup:
#   Servo on GP0
#   DC motor via L9110 H-bridge driver on GP28, GP27 (they're on different PWM channels)
#   Stepper motor via DRV8833 driver breakout on GP21, GP20, GP19, GP18
#   Button on GP3
#   MOSFET driving solenoid on GP14

import time
import board
from digitalio import DigitalInOut, Direction, Pull
import pwmio
from adafruit_motor import stepper, motor, servo

print("*** Welcome to the Raspberry Pi RP2040 Pico Motor Party Demo ***")

led = DigitalInOut(board.LED)
led.direction = Direction.OUTPUT
led.value = True


def blink(times):
    for _ in range(times):
        led.value = False
        time.sleep(0.1)
        led.value = True
        time.sleep(0.1)


# Mode button setup
mode_button = DigitalInOut(board.GP3)
mode_button.direction = Direction.INPUT
mode_button.pull = Pull.UP
mode = -1  # track different demo modes

# Solenoid setup
solenoid = DigitalInOut(board.GP14)  # pin drives a MOSFET
solenoid.direction = Direction.OUTPUT
solenoid.value = False

strike_time = 0.04
recover_time = 0.04

# Solenoid test
def solenoid_test(loops):
    print("solenoid test")
    for _ in range(loops):
        solenoid.value = True
        time.sleep(strike_time)
        solenoid.value = False
        time.sleep(recover_time)
        time.sleep(0.1)


# Servo setup
pwm_servo = pwmio.PWMOut(board.GP0, duty_cycle=2 ** 15, frequency=50)
servo1 = servo.Servo(
    pwm_servo, min_pulse=500, max_pulse=2200
)  # tune pulse for specific servo

# Servo test
def servo_direct_test():
    print("servo test: 90")
    servo1.angle = 90
    time.sleep(2)
    print("servo test: 0")
    servo1.angle = 0
    time.sleep(2)
    print("servo test: 90")
    servo1.angle = 90
    time.sleep(2)
    print("servo test: 180")
    servo1.angle = 180
    time.sleep(2)


# Servo smooth test
def servo_smooth_test():
    print("servo smooth test: 180 - 0, -1º steps")
    for angle in range(180, 0, -1):  # 180 - 0 degrees, -1º at a time.
        servo1.angle = angle
        time.sleep(0.01)
    time.sleep(1)
    print("servo smooth test: 0 - 180, 1º steps")
    for angle in range(0, 180, 1):  # 0 - 180 degrees, 1º at a time.
        servo1.angle = angle
        time.sleep(0.01)
    time.sleep(1)


# DC motor setup
pwm_a = pwmio.PWMOut(board.GP28, frequency=50)
pwm_b = pwmio.PWMOut(board.GP27, frequency=50)
motor1 = motor.DCMotor(pwm_a, pwm_b)

# DC motor test
def dc_motor_test():
    print("DC motor test: 0.5")
    motor1.throttle = 0.5
    time.sleep(0.5)
    print("DC motor test: None")
    motor1.throttle = None
    time.sleep(0.5)
    print("DC motor test: -0.5")
    motor1.throttle = -0.5
    time.sleep(0.5)
    print("DC motor test: None")
    motor1.throttle = None
    time.sleep(0.5)
    print("DC motor test: 0.9")
    motor1.throttle = 1.0
    time.sleep(0.5)
    print("DC motor test: None")
    motor1.throttle = None
    time.sleep(0.5)
    print("DC motor test: -0.9")
    motor1.throttle = -1.0
    time.sleep(0.5)
    print("DC motor test: None")
    motor1.throttle = None
    time.sleep(0.5)


# Stepper motor setup
DELAY = 0.006  # fastest is ~ 0.004, 0.01 is still very smooth, gets steppy after that
STEPS = 513  # this is a full 360º
coils = (
    DigitalInOut(board.GP21),  # A1
    DigitalInOut(board.GP20),  # A2
    DigitalInOut(board.GP19),  # B1
    DigitalInOut(board.GP18),  # B2
)
for coil in coils:
    coil.direction = Direction.OUTPUT

stepper_motor = stepper.StepperMotor(
    coils[0], coils[1], coils[2], coils[3], microsteps=None
)


def stepper_fwd():
    for _ in range(STEPS):
        stepper_motor.onestep(direction=stepper.FORWARD)
        time.sleep(DELAY)
    stepper_motor.release()


def stepper_back():
    for _ in range(STEPS):
        stepper_motor.onestep(direction=stepper.BACKWARD)
        time.sleep(DELAY)
    stepper_motor.release()


# Stepper test
def stepper_test():
    print("stepper test: forward")
    for _ in range(2):
        stepper_fwd()
    time.sleep(1)
    print("stepper test: backward")
    for _ in range(2):
        stepper_back()
    time.sleep(1)


def run_test(testnum):
    if testnum == 0:
        solenoid_test(4)
    elif testnum == 1:
        servo_direct_test()
    elif testnum == 2:
        servo_smooth_test()
    elif testnum == 3:
        dc_motor_test()
    elif testnum == 4:
        stepper_test()


while True:
    if not mode_button.value:
        blink(2)
        mode = (mode + 1) % 5
        print("switch to mode %d" % (mode))
        time.sleep(0.8)  # big debounce
        run_test(mode)
