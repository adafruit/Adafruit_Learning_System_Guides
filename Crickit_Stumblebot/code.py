# SPDX-FileCopyrightText: 2018 Dano Wall for Adafruit Industries
# SPDX-FileCopyrightText: 2018 Anne Barela for Adafruit Industries
#
# SPDX-License-Identifier: MIT

# Stumble Bot, coded in CircuitPython
# Using an Adafruit Circuit Playground Express, Crickit, and 2 servos
# Dano Wall, Anne Barela for Adafruit Industries, MIT License, May, 2018
#
import time
from digitalio import DigitalInOut, Direction, Pull
from adafruit_seesaw.seesaw import Seesaw
from adafruit_seesaw.pwmout import PWMOut

from adafruit_motor import servo
from busio import I2C
import board

# Create seesaw object for Circuit Playground Express to talk to Crickit
i2c = I2C(board.SCL, board.SDA)
seesaw = Seesaw(i2c)

led = DigitalInOut(board.D13)            # Set up Red LED
led.direction = Direction.OUTPUT

button_A = DigitalInOut(board.BUTTON_A)  # Set up switch A
button_A.direction = Direction.INPUT
button_A.pull = Pull.DOWN

# Create servos list
servos = []
for ss_pin in (17, 16):  # Only use 2 servos, append , 15, 14 if using 4
    pwm = PWMOut(seesaw, ss_pin)
    pwm.frequency = 50
    _servo = servo.Servo(pwm, min_pulse=600, max_pulse=2500)
    _servo.angle = 90   # starting angle, middle
    servos.append(_servo)

def servo_front(direction):
    if direction > 0:
        index = 50
        while index <= 90:
            servos[1].angle = index
            time.sleep(0.040)
            index = index + 1
    if direction < 0:
        index = 90
        while index >= 50:
            servos[1].angle = index
            time.sleep(0.040)
            index = index - 1
    time.sleep(0.002)

def servo_back(direction):
    if direction > 0:
        index = 65
        while index <= 95:
            servos[0].angle = index
            time.sleep(0.040)
            index = index + 3
    if direction < 0:
        index = 95
        while index >= 65:
            servos[0].angle = index
            time.sleep(0.040)
            index = index - 3
    time.sleep(0.020)

print("Its Stumble Bot Time")

while True:
    if button_A.value:  # If button A is pressed, start bot
        led.value = True  # Turn on LED 13 to show we're gone!
        for i in range(5):
            print("back 1")
            servo_back(1)
            time.sleep(0.100)
            print("front 1")
            servo_front(1)
            time.sleep(0.100)
            print("back 2")
            servo_back(-1)
            time.sleep(0.100)
            print("front 2")
            servo_front(-1)
            time.sleep(0.100)
        led.value = False
    # end if
# end while
