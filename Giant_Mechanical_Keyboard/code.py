# Big Control Alt Delete Board
# Code is written for the Circuit Playground Express board:
#   https://www.adafruit.com/product/3333
# Needs the NeoPixel module installed:
#   https://github.com/adafruit/Adafruit_CircuitPython_NeoPixel
# Author: Collin Cunningham
# License: MIT License (https://opensource.org/licenses/MIT)

import time

import board
import neopixel
from adafruit_hid.keyboard import Keyboard
from adafruit_hid.keyboard_layout_us import KeyboardLayoutUS
from adafruit_hid.keycode import Keycode
from digitalio import DigitalInOut, Direction, Pull

pixels = neopixel.NeoPixel(board.NEOPIXEL, 10, brightness=.2)
pixels.fill((0, 0, 0))
pixels.show()

# The pins connected to each switch/button
buttonpins = [board.A7, board.A5, board.A3]
# The pins connected to each LED
ledpins = [board.A6, board.A4, board.A2]

# our array of button & LED objects
buttons = []
leds = []

# The keycode sent for each switch/button, will be paired with a control key
buttonkeys = [Keycode.CONTROL, Keycode.ALT, Keycode.DELETE]
buttonspressed = [False, False, False]
buttonspressedlast = [False, False, False]

# the keyboard object!
kbd = Keyboard()
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


def lightneopixels():
    vals = [0, 0, 0]
    # if switch 0 pressed, show blue
    if buttonspressed[0]:
        vals[2] = 255
    # if switch 1 pressed, show yellow
    if buttonspressed[1]:
        vals[0] = 127
        vals[1] = 64
    # if switch 2 pressed, show red
    if buttonspressed[2]:
        vals[0] = 255
    # if all pressed, show white
    if buttonspressed[0] and buttonspressed[1] and buttonspressed[2]:
        vals = [255, 255, 255]
    # if 0 & 1 pressed, show green
    if buttonspressed[0] and buttonspressed[1] and not buttonspressed[2]:
        vals = [0, 255, 0]
    pixels.fill((vals[0], vals[1], vals[2]))
    pixels.show()


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
    lightneopixels()
    # save pressed buttons as pressed last
    buttonspressedlast = list(buttonspressed)
    time.sleep(0.01)
