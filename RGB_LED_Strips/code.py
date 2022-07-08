# SPDX-FileCopyrightText: 2017 Tony DiCola for Adafruit Industries
#
# SPDX-License-Identifier: MIT

import time

import board
import pwmio

RED_PIN = board.D5  # Red LED pin
GREEN_PIN = board.D6  # Green LED pin
BLUE_PIN = board.D3  # Blue LED pin

FADE_SLEEP = 10  # Number of milliseconds to delay between changes.
# Increase to slow down, decrease to speed up.

# Define PWM outputs:
red = pwmio.PWMOut(RED_PIN)
green = pwmio.PWMOut(GREEN_PIN)
blue = pwmio.PWMOut(BLUE_PIN)


# Function to simplify setting duty cycle to percent value.


def duty_cycle(percent):
    return int(percent / 100.0 * 65535.0)


# Fade from nothing up to full red.
for i in range(100):
    red.duty_cycle = duty_cycle(i)
    time.sleep(FADE_SLEEP / 1000)

# Now fade from violet (red + blue) down to red.
for i in range(100, -1, -1):
    blue.duty_cycle = duty_cycle(i)
    time.sleep(FADE_SLEEP / 1000)

# Fade from red to yellow (red + green).
for i in range(100):
    green.duty_cycle = duty_cycle(i)
    time.sleep(FADE_SLEEP / 1000)

# Fade from yellow to green.
for i in range(100, -1, -1):
    red.duty_cycle = duty_cycle(i)
    time.sleep(FADE_SLEEP / 1000)

# Fade from green to teal (blue + green).
for i in range(100):
    blue.duty_cycle = duty_cycle(i)
    time.sleep(FADE_SLEEP / 1000)

# Fade from teal to blue.
for i in range(100, -1, -1):
    green.duty_cycle = duty_cycle(i)
    time.sleep(FADE_SLEEP / 1000)
