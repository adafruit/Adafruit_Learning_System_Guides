# SPDX-FileCopyrightText: 2021 Collin Cunningham for Adafruit Industries
# SPDX-License-Identifier: MIT

import time
import board
import usb_hid
from adafruit_hid.keyboard import Keyboard
from adafruit_hid.keyboard_layout_us import KeyboardLayoutUS
from adafruit_hid.keycode import Keycode
from digitalio import DigitalInOut, Direction, Pull

# The pins connected to each switch/button
buttonpins = [board.D3, board.D4, board.D5]
# The pins connected to each LED
ledpins = [board.D2, board.D6, board.D7]

# our array of button & LED objects
buttons = []
leds = []

# The keycode sent for each switch/button
buttonkeys = [Keycode.B, Keycode.C, Keycode.A]
buttonspressed = [False, False, False]
buttonspressedlast = [False, False, False]

# the keyboard object!
kbd = Keyboard(usb_hid.devices)
# we're americans :)
layout = KeyboardLayoutUS(kbd)

# make all button pin objects, make them inputs w/pullups
for pin in buttonpins:
    button = DigitalInOut(pin)
    button.direction = Direction.INPUT
    button.pull = Pull.UP
    buttons.append(button)

# make all LED objects, make them outputs
for pin in ledpins:
    led = DigitalInOut(pin)
    led.direction = Direction.OUTPUT
    leds.append(led)

# set up the status LED
statusled = DigitalInOut(board.D13)
statusled.direction = Direction.OUTPUT

print("Waiting for button presses")


def pressbutton(index):
    switch_led = leds[index]  # find the switch LED
    k = buttonkeys[index]  # get the corresp. keycode/str
    switch_led.value = True  # turn on LED
    kbd.press(k)  # send keycode


def releasebutton(index):
    switch_led = leds[index]  # find the switch LED
    k = buttonkeys[index]  # get the corresp. keycode/str
    switch_led.value = False  # turn on LED
    kbd.release(k)  # send keycode

while True:
    # check each button
    for button in buttons:
        i = buttons.index(button)
        if button.value is False:  # button is pressed?
            buttonspressed[i] = True  # save pressed button
            # was button not pressed last time?
            if buttonspressedlast[i] is False:
                print("Pressed #%d" % i)
                pressbutton(i)
        else:
            buttonspressed[i] = False  # button was not pressed
            if buttonspressedlast[i] is True:  # was button pressed last time?
                print("Released #%d" % i)
                releasebutton(i)
    #lightneopixels()
    # save pressed buttons as pressed last
    buttonspressedlast = list(buttonspressed)
    time.sleep(0.01)
