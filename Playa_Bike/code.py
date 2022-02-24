# SPDX-FileCopyrightText: 2019 Erin St Blaine for Adafruit Industries
#
# SPDX-License-Identifier: MIT

import time
import board
from rainbowio import colorwheel
import adafruit_rgbled
import digitalio

POWER_PIN = board.D10

enable = digitalio.DigitalInOut(POWER_PIN)
enable.direction = digitalio.Direction.OUTPUT
enable.value = True

# Pin the Red LED is connected to
RED_LED = board.D11

# Pin the Green LED is connected to
GREEN_LED = board.D12

# Pin the Blue LED is connected to
BLUE_LED = board.D13

# Create the RGB LED object
led = adafruit_rgbled.RGBLED(RED_LED, GREEN_LED, BLUE_LED)

# Optionally, you can also create the RGB LED object with inverted PWM
# led = adafruit_rgbled.RGBLED(RED_LED, GREEN_LED, BLUE_LED, invert_pwm=True)

def rainbow_cycle(wait):
    for i in range(255):
        i = (i + 1) % 256
        led.color = colorwheel(i)
        time.sleep(wait)

while True:
    # rainbow cycle the RGB LED
    rainbow_cycle(0.1)
