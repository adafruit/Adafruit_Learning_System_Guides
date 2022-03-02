# SPDX-FileCopyrightText: 2021 Kattni Rembor for Adafruit Industries
#
# SPDX-License-Identifier: MIT

"""
LED example for Pico. Blinks external LED on and off.

REQUIRED HARDWARE:
* LED on pin GP14.
"""
import time
import board
import digitalio

led = digitalio.DigitalInOut(board.GP14)
led.direction = digitalio.Direction.OUTPUT

while True:
    led.value = True
    time.sleep(0.5)
    led.value = False
    time.sleep(0.5)
