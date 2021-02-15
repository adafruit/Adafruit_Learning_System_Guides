# SPDX-FileCopyrightText: 2021 jedgarpark for Adafruit Industries
# SPDX-License-Identifier: MIT

# Pico servo demo
# Hardware setup:
#   Servo on GP0 with external 5V power supply
#   Button on GP3 and ground

import time
import board
from digitalio import DigitalInOut, Direction, Pull
import pwmio
from adafruit_motor import servo

print("Servo test")

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


def run_test(testnum):
    if testnum is 0:
        servo_direct_test()
    elif testnum is 1:
        servo_smooth_test()


while True:
    if not button.value:
        blink(2)
        mode = (mode + 1) % 2
        print("switch to mode %d" % (mode))
        time.sleep(0.8)  # big debounce
        run_test(mode)
