# SPDX-FileCopyrightText: 2018 John Park for Adafruit Industries
#
# SPDX-License-Identifier: MIT

# Gemma M0 Password Vault
# press cap touch pads to enter strong passwords over USB

import time

import board
import touchio
import usb_hid
from adafruit_hid.keyboard import Keyboard
from adafruit_hid.keyboard_layout_us import KeyboardLayoutUS
from digitalio import DigitalInOut, Direction

led = DigitalInOut(board.D13)
led.direction = Direction.OUTPUT

touch0 = touchio.TouchIn(board.A0)
touch1 = touchio.TouchIn(board.A1)
touch2 = touchio.TouchIn(board.A2)

# the keyboard object
# sleep for a bit to avoid a race condition on some systems
time.sleep(1)
kbd = Keyboard(usb_hid.devices)
layout = KeyboardLayoutUS(kbd)

while True:
    if touch0.value:
        led.value = True
        print("A0 touched!")
        layout.write("?F3ErPs5.C.m.0.d.S.")  # enter your own password here
        time.sleep(1)

    if touch1.value:
        led.value = True
        print("A1 touched!")
        layout.write("6@LKNs(WV[vq6N")  # enter your own password here
        time.sleep(1)

    if touch2.value:
        led.value = True
        print("A2 touched!")
        layout.write("3Ff0rT@9j2y&")  # enter your own password here
        time.sleep(1)

    time.sleep(0.01)

    print("Waiting for cap touches")
    # turn off the LED
    led.value = False

    time.sleep(0.01)
