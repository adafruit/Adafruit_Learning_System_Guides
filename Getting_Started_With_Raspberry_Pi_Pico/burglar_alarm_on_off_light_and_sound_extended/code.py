# SPDX-FileCopyrightText: 2021 Kattni Rembor for Adafruit Industries
#
# SPDX-License-Identifier: MIT

"""
A burglar alarm with two motion sensors example for Pico. Slow flashing LED indicates alarm is
ready. Quick flashing LED and beeping buzzer indicate alarm has been triggered.

REQUIRED HARDWARE:
* PIR sensor on pin GP28.
* PIR sensor on pin GP22.
* LED on pin GP13.
* Piezo buzzer on pin GP14.
"""
import time
import board
import digitalio
import pwmio

pir_one = digitalio.DigitalInOut(board.GP28)
pir_one.direction = digitalio.Direction.INPUT
pir_two = digitalio.DigitalInOut(board.GP22)
pir_two.direction = digitalio.Direction.INPUT
led = digitalio.DigitalInOut(board.GP13)
led.direction = digitalio.Direction.OUTPUT
buzzer = pwmio.PWMOut(board.GP14, frequency=660, duty_cycle=0, variable_frequency=True)

motion_detected_one = False
motion_detected_two = False
while True:
    if pir_one.value and not motion_detected_one:
        print("ALARM! Motion detected in bedroom!")
        motion_detected_one = True

    if pir_two.value and not motion_detected_two:
        print("ALARM! Motion detected in living room!")
        motion_detected_two = True

    if pir_one.value or pir_two.value:
        led.value = True
        buzzer.duty_cycle = 2 ** 15
        time.sleep(0.1)
        led.value = False
        buzzer.duty_cycle = 0
        time.sleep(0.1)

    else:
        motion_detected_one = False
        motion_detected_two = False

        led.value = True
        time.sleep(0.5)
        led.value = False
        time.sleep(0.5)
