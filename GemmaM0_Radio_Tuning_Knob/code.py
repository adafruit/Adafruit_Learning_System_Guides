# SPDX-FileCopyrightText: 2018 John Edgar Park for Adafruit Industries
#
# SPDX-License-Identifier: MIT

# Gemma Radio Tuning Knob
# for fine tuning Software Defined Radio CubicSDR software
# 10k pot hooked to 3v, A2, and D2 acting as GND

import time

import board
import usb_hid
from adafruit_hid.keyboard import Keyboard
from adafruit_hid.keycode import Keycode
from analogio import AnalogIn
from digitalio import DigitalInOut, Direction

d2_ground = DigitalInOut(board.D2)
d2_ground.direction = Direction.OUTPUT
d2_ground.value = False
analog2in = AnalogIn(board.A2)

led = DigitalInOut(board.D13)
led.direction = Direction.OUTPUT

pot_max = 3.29
pot_min = 0.00
step = (pot_max - pot_min) / 10.0
last_knob = 0


def steps(x):
    return round((x - pot_min) / step)


def getVoltage(pin):
    return (pin.value * 3.3) / 65536


def spamKey(code):
    knobkeys = [Keycode.RIGHT_BRACKET, Keycode.RIGHT_BRACKET,
                Keycode.RIGHT_BRACKET, Keycode.RIGHT_BRACKET,
                Keycode.RIGHT_BRACKET, Keycode.SPACE,
                Keycode.LEFT_BRACKET, Keycode.LEFT_BRACKET,
                Keycode.LEFT_BRACKET, Keycode.LEFT_BRACKET,
                Keycode.LEFT_BRACKET]
    spamRate = [0.01, 0.05, 0.125, 0.25, 0.5,
                0.5, 0.5, 0.25, 0.125, 0.05, 0.01]
    kbd = Keyboard(usb_hid.devices)
    kbd.press(knobkeys[code])  # which keycode is entered
    kbd.release_all()
    time.sleep(spamRate[code])  # how fast the key is spammed


while True:
    knob = (getVoltage(analog2in))
    if steps(knob) == 5:  # the center position is active
        led.value = True
    elif steps(knob) != 5:
        led.value = False
        spamKey(steps(knob))
