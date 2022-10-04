# SPDX-FileCopyrightText: 2022 Noe Ruiz for Adafruit Industries
# SPDX-License-Identifier: MIT
# Adafruit nOOds lantern with "analog" (PWM) brightness control using GPIO.
# Uses 6 nOOds, anode (+) to GPIO pin, cathode (-) to ground.
# A current-limiting resistor (e.g. 10 Ohm) can go at either end.

import math
import time
import board
import pwmio
from digitalio import DigitalInOut, Direction, Pull

PINS = (board.SCK, board.MOSI, board.A1, board.A3, board.MISO, board.A2) # List of pins, one per nOOd
GAMMA = 2.6  # For perceptually-linear brightness

# Convert pin number list to PWMOut object list
pin_list = [pwmio.PWMOut(pin, frequency=1000, duty_cycle=0) for pin in PINS]

# Button switch set up
switch = DigitalInOut(board.A0)
switch.direction = Direction.INPUT
switch.pull = Pull.UP

# LED set up
led = DigitalInOut(board.TX)
led.direction = Direction.OUTPUT

while True: # Repeat forever...
    # If the button is pressed turn on LED n00ds
    if switch.value:
        for i, pin in enumerate(pin_list): # For each pin...
            # Calc sine wave, phase offset for each pin, with gamma correction.
            # If using red, green, blue nOOds, you'll get a cycle of hues.
            phase = (time.monotonic() - 2 * i / len(PINS)) * math.pi
            brightness = int((math.sin(phase) + 1.0) * 0.5 ** GAMMA * 65535 + 0.5)
            pin.duty_cycle = brightness
        led.value = True # Turn button LED on
    else: # Otherwise turn LED n00ds off
        for i, pin in enumerate(pin_list):
            pin.duty_cycle = 0
        led.value = False # Turn button LED off

    time.sleep(.01)
