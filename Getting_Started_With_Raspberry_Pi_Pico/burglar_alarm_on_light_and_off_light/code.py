# SPDX-FileCopyrightText: 2021 Kattni Rembor for Adafruit Industries
#
# SPDX-License-Identifier: MIT

"""
A burglar alarm example for Pico. Slow flashing LED indicates alarm is ready. Quick flashing LED
indicates alarm has been triggered.

REQUIRED HARDWARE:
* PIR sensor on pin GP28.
* LED on pin GP13.
"""
import time
import board
import digitalio

pir = digitalio.DigitalInOut(board.GP28)
pir.direction = digitalio.Direction.INPUT
led = digitalio.DigitalInOut(board.GP13)
led.direction = digitalio.Direction.OUTPUT

motion_detected = False
while True:
    if pir.value and not motion_detected:
        print("ALARM! Motion detected!")
        motion_detected = True

    if pir.value:
        led.value = True
        time.sleep(0.1)
        led.value = False
        time.sleep(0.1)

    else:
        motion_detected = False
        led.value = True
        time.sleep(0.5)
        led.value = False
        time.sleep(0.5)
