# SPDX-FileCopyrightText: 2021 jedgarpark for Adafruit Industries
# SPDX-License-Identifier: MIT

# Pico stepper demo
# Hardware setup:
#    Stepper motor via DRV8833 driver breakout on GP21, GP20, GP19, GP18
#   external power supply
#   Button on GP3 and ground

import time
import board
from digitalio import DigitalInOut, Direction, Pull
from adafruit_motor import stepper

print("Stepper test")

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
button = DigitalInOut(board.GP3)
button.direction = Direction.INPUT
button.pull = Pull.UP
mode = -1  # track state of button mode

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
    print("stepper forward")
    for _ in range(STEPS):
        stepper_motor.onestep(direction=stepper.FORWARD)
        time.sleep(DELAY)
    stepper_motor.release()


def stepper_back():
    print("stepper backward")
    for _ in range(STEPS):
        stepper_motor.onestep(direction=stepper.BACKWARD)
        time.sleep(DELAY)
    stepper_motor.release()


def run_test(testnum):
    if testnum is 0:
        stepper_fwd()
    elif testnum is 1:
        stepper_back()


while True:
    if not button.value:
        blink(2)
        mode = (mode + 1) % 2
        print("switch to mode %d" % (mode))
        time.sleep(0.8)  # big debounce
        run_test(mode)
