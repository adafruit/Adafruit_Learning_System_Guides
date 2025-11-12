# SPDX-FileCopyrightText: 2018 Dano Wall for Adafruit Industries
# SPDX-FileCopyrightText: 2018 Anne Barela for Adafruit Industries
#
# SPDX-License-Identifier: MIT

# Stumble bot, coded in CircuitPython
# Using an Adafruit Circuit Playground Express, Crickit, and 2 servos
# Dano Wall, Anne Barela for Adafruit Industries, MIT License, May, 2018
#
import time
import board
from digitalio import DigitalInOut, Direction, Pull
from adafruit_crickit import crickit

led = DigitalInOut(board.D13)            # Set up Red LED
led.direction = Direction.OUTPUT

button_A = DigitalInOut(board.BUTTON_A)  # Set up switch A
button_A.direction = Direction.INPUT
button_A.pull = Pull.DOWN

# Create servos list
servos = [crickit.servo_1, crickit.servo_2]

# TowerPro servos like 500/2500 pulsewidths
servos[0].set_pulse_width_range(min_pulse=500, max_pulse=2500)
servos[1].set_pulse_width_range(min_pulse=500, max_pulse=2500)

# starting angle, middle
servos[1].angle = 90
servos[0].angle = 90

def servo_front(direction):
    if direction > 0:
        index = 50
        while index <= 100:
            servos[1].angle = index
            time.sleep(0.040)
            index = index + 2
    if direction < 0:
        index = 100
        while index >= 50:
            servos[1].angle = index
            time.sleep(0.040)
            index = index - 2
    time.sleep(0.002)

def servo_back(direction):
    if direction > 0:
        index = 60
        while index <= 90:
            servos[0].angle = index
            time.sleep(0.040)
            index = index + 4
    if direction < 0:
        index = 100
        while index >= 50:
            servos[0].angle = index
            time.sleep(0.040)
            index = index - 4
    time.sleep(0.020)

print("Its Stumble Bot Time")

while True:
    if button_A.value:     # If button A is pressed, start bot
        led.value = True   # Turn on LED 13 to show we're gone!
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
