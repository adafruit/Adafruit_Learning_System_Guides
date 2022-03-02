# SPDX-FileCopyrightText: 2021 Kattni Rembor for Adafruit Industries
#
# SPDX-License-Identifier: MIT

"""
Two-player reaction game example for Pico. LED turns on for between 5 and 10 seconds. Once it
turns off, try to press the button faster than the other player to see who wins.

REQUIRED HARDWARE:
* LED on pin GP13.
* Button switch on pin GP14.
* Button switch on GP16.
"""
import time
import random
import board
import digitalio

led = digitalio.DigitalInOut(board.GP13)
led.direction = digitalio.Direction.OUTPUT
button_one = digitalio.DigitalInOut(board.GP14)
button_one.switch_to_input(pull=digitalio.Pull.DOWN)
button_two = digitalio.DigitalInOut(board.GP16)
button_two.switch_to_input(pull=digitalio.Pull.DOWN)

led.value = True
time.sleep(random.randint(5, 10))
led.value = False
while True:
    if button_one.value:
        print("Player one wins!")
        break
    if button_two.value:
        print("Player two wins!")
        break
