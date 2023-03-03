# SPDX-FileCopyrightText: 2023 Carter Nelson for Adafruit Industries
#
# SPDX-License-Identifier: MIT

# Example code for recording and playing back servo motion with a
# analog feedback servo
# pylint: disable=redefined-outer-name
 
import time
import board
import pwmio
import keypad
from simpleio import map_range
from adafruit_motor import servo
from analogio import AnalogIn
from digitalio import DigitalInOut, Direction

# Pin setup
RECORD_PIN = board.D10
PLAY_PIN = board.D9
LED_PIN = board.D13
SERVO_PIN = board.A1
FEEDBACK_PIN = board.A3

# Record setup
CALIB_MIN = 15377
CALIB_MAX = 42890
ANGLE_MIN = 0
ANGLE_MAX = 180
SAMPLE_COUNT = 512
SAMPLE_DELAY = 0.025

# Setup buttons
buttons = keypad.Keys((RECORD_PIN, PLAY_PIN), value_when_pressed=False, pull=True)

# Setup LED
led = DigitalInOut(LED_PIN)
led.direction = Direction.OUTPUT
led.value = False

# Setup servo
pwm = pwmio.PWMOut(SERVO_PIN, duty_cycle=2 ** 15, frequency=50)
servo = servo.Servo(pwm)
servo.angle = None

# Setup feedback
feedback = AnalogIn(FEEDBACK_PIN)

# Servo positions stored here
position = [None]*SAMPLE_COUNT

print("Servo RecordPlay")

def play_servo():
    print("Playing...", end="")
    count = 0
    while True:
        print(".", end="")
        event = buttons.events.get()
        if event:
            if event.pressed and event.key_number == 1:
                break
        angle = position[count]
        if angle is None:
            break
        servo.angle = angle
        count += 1
        if count >= SAMPLE_COUNT:
            break
        time.sleep(SAMPLE_DELAY)
    print("Done.")
    servo.angle = None
    time.sleep(0.250)

def record_servo():
    for i in range(len(position)):
        position[i] = None
    servo.angle = None
    led.value = True
    print("Recording...", end="")
    count = 0
    while True:
        print(".", end='')
        event = buttons.events.get()
        if event:
            if event.pressed and event.key_number == 0:
                break
        position[count] = map_range(feedback.value, CALIB_MIN, CALIB_MAX, ANGLE_MIN, ANGLE_MAX)
        count += 1
        if count >= SAMPLE_COUNT:
            break
        time.sleep(SAMPLE_DELAY)
    led.value = False
    print("Done.")
    time.sleep(0.250)

while True:
    event = buttons.events.get()
    if event:
        if event.pressed:
            if event.key_number == 0:
                record_servo()
            elif event.key_number == 1:
                play_servo()
