# SPDX-FileCopyrightText: 2017 Limor Fried for Adafruit Industries
#
# SPDX-License-Identifier: MIT

# CircuitPlayground demo - Keyboard emu

import time

import board
import usb_hid
from adafruit_hid.keyboard import Keyboard
from adafruit_hid.keyboard_layout_us import KeyboardLayoutUS
from adafruit_hid.keycode import Keycode
from digitalio import DigitalInOut, Direction, Pull

# A simple neat keyboard demo in circuitpython

# The button pins we'll use, each will have an internal pullup
buttonpins = [board.D2, board.D1, board.D0]
# our array of button objects
buttons = []
# The keycode sent for each button, will be paired with a control key
buttonkeys = [Keycode.A, Keycode.B, "Hello World!\n"]
controlkey = Keycode.SHIFT

# the keyboard object!
# sleep for a bit to avoid a race condition on some systems
time.sleep(1)
kbd = Keyboard(usb_hid.devices)
# we're americans :)
layout = KeyboardLayoutUS(kbd)

# make all pin objects, make them inputs w/pullups
for pin in buttonpins:
    button = DigitalInOut(pin)
    button.direction = Direction.INPUT
    button.pull = Pull.UP
    buttons.append(button)

led = DigitalInOut(board.D13)
led.direction = Direction.OUTPUT

print("Waiting for button presses")

while True:
    # check each button
    for button in buttons:
        if not button.value:  # pressed?
            i = buttons.index(button)
            print("Button #%d Pressed" % i)

            # turn on the LED
            led.value = True

            while not button.value:
                pass  # wait for it to be released!
            # type the keycode or string
            k = buttonkeys[i]  # get the corresp. keycode/str
            if isinstance(k, str):
                layout.write(k)
            else:
                kbd.press(controlkey, k)  # press...
                kbd.release_all()  # release!

            # turn off the LED
            led.value = False

    time.sleep(0.01)
