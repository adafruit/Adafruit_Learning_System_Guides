# SPDX-FileCopyrightText: 2021 Kattni Rembor for Adafruit Industries
#
# SPDX-License-Identifier: MIT

"""Traffic light simulator example for Pico. Turns on red, amber and green LEDs in traffic
light-like sequence.

REQUIRED HARDWARE:
* Red LED on pin GP11.
* Amber LED on pin GP14.
* Green LED on pin GP13.
"""
import time
import board
import digitalio

red_led = digitalio.DigitalInOut(board.GP11)
red_led.direction = digitalio.Direction.OUTPUT
amber_led = digitalio.DigitalInOut(board.GP14)
amber_led.direction = digitalio.Direction.OUTPUT
green_led = digitalio.DigitalInOut(board.GP13)
green_led.direction = digitalio.Direction.OUTPUT

while True:
    red_led.value = True
    time.sleep(5)
    amber_led.value = True
    time.sleep(2)
    red_led.value = False
    amber_led.value = False
    green_led.value = True
    time.sleep(5)
    green_led.value = False
    amber_led.value = True
    time.sleep(3)
    amber_led.value = False
