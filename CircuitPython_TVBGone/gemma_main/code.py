# SPDX-FileCopyrightText: 2018 John Edgar Park for Adafruit Industries
#
# SPDX-License-Identifier: MIT

# Gemma M0 version of TVBgone!
import array
import time

import adafruit_dotstar
import board
import pwmio
import pulseio
from digitalio import DigitalInOut, Direction

# pylint: disable=eval-used

pixel = adafruit_dotstar.DotStar(
    board.APA102_SCK, board.APA102_MOSI, 1, brightness=0.2)
pixel.fill((0, 0, 0))

# Button to see output debug
led = DigitalInOut(board.D13)
led.direction = Direction.OUTPUT

pwm = pwmio.PWMOut(board.A2, frequency=38000,
                     duty_cycle=2 ** 15, variable_frequency=True)
pulse = pulseio.PulseOut(pwm)

time.sleep(0.5)  # Give a half second before starting

# gooooo!
f = open("/codes.txt", "r")
for line in f:
    code = eval(line)
    print(code)
    pwm.frequency = code['freq']
    led.value = True
    # If this is a repeating code, extract details
    try:
        repeat = code['repeat']
        delay = code['repeat_delay']
    except KeyError:  # by default, repeat once only!
        repeat = 1
        delay = 0
    # The table holds the on/off pairs
    table = code['table']
    pulses = []  # store the pulses here
    # Read through each indexed element
    for i in code['index']:
        pulses += table[i]  # and add to the list of pulses
    pulses.pop()  # remove one final 'low' pulse

    for i in range(repeat):
        pulse.send(array.array('H', pulses))
        time.sleep(delay)
    led.value = False
    time.sleep(code['delay'])

f.close()
