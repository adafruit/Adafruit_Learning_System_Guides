# SPDX-FileCopyrightText: 2021 jedgarpark for Adafruit Industries
# SPDX-License-Identifier: MIT

# This example uses an MOSFET transistor circuit to drive a solenoid from a Pico RP2040 digitalio pin
# Hardware setup:
#   Button on GP3 to gnd (uses internal pull up)
#   MOSFET driving solenoid on GP14 w protection diode and 47uF capacitor across power rails
#   external power source should be proper voltage and current for solenoid, not USB power

import time
import board
from digitalio import DigitalInOut, Direction, Pull

print("*** Solenoid Demo ***")

led = DigitalInOut(board.LED)  # onboard LED setup
led.direction = Direction.OUTPUT
led.value = True


def blink(times):
    for _ in range(times):
        led.value = False
        time.sleep(0.1)
        led.value = True
        time.sleep(0.1)


# Mode button setup
button = DigitalInOut(board.GP3)
button.direction = Direction.INPUT
button.pull = Pull.UP

# Solenoid setup
solenoid = DigitalInOut(board.GP14)  #  pin drives a MOSFET
solenoid.direction = Direction.OUTPUT
solenoid.value = False

strike_time = 0.05  # adjust for coil on time  range ~0.05 - ? (beware heat/power drain beyond a few seconds)
recover_time = 0.20  # adjust for coil off time/pause between strikes


def solenoid_strike(loops):  # solenoid strike function
    print("solenoid test")
    for i in range(loops):
        solenoid.value = True
        time.sleep(strike_time)
        solenoid.value = False
        time.sleep(recover_time)
        time.sleep(0.1)


while True:
    if not button.value:
        blink(1)
        solenoid_strike(4)
