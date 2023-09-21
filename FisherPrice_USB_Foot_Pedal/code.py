# SPDX-FileCopyrightText: 2023 Robert Dale Smith for Adafruit Industries
#
# SPDX-License-Identifier: MIT
# The Fisher-Price Kick and Play Piano Gym has five buttons that are
# active high. Pressed = 1, Released = 0. This code turns that into
# keyboard key press, key combos, and/or key press/combo macros.

import time
import board
import usb_hid
from adafruit_hid.keyboard import Keyboard
from adafruit_hid.keycode import Keycode
from adafruit_hid.keyboard_layout_us import KeyboardLayoutUS
from digitalio import DigitalInOut, Direction, Pull

# Set up a keyboard device.
kbd = Keyboard(usb_hid.devices)
layout = KeyboardLayoutUS(kbd)

# Setup the buttons with internal pull-down resistors
buttons = []
for pin in [board.A0, board.A2, board.CLK, board.D2, board.D3]: # kb2040 pins
    button = DigitalInOut(pin)
    button.direction = Direction.INPUT
    button.pull = Pull.DOWN
    buttons.append(button)

# Each button corresponds to a key or key combination or a sequence of keys
keys = [
    Keycode.A,
    (Keycode.COMMAND, Keycode.TAB),
    [
        Keycode.UP_ARROW,
        Keycode.ENTER
    ],
    [
        Keycode.END,
        (Keycode.SHIFT, Keycode.HOME),
        (Keycode.COMMAND, Keycode.C),
    ],
    [
        (Keycode.CONTROL, Keycode.A),
        'Hello World',
        Keycode.PERIOD
    ]
]

while True:
    # check each button
    for button, key in zip(buttons, keys):
        if button.value:  # button is pressed
            if isinstance(key, tuple):
                kbd.press(*key)
                kbd.release_all()
            elif isinstance(key, list):
                for macro_key in key:
                    if isinstance(macro_key, str):  # print a string
                        layout.write(macro_key)
                    elif isinstance(macro_key, tuple):  # press combo keys
                        kbd.press(*macro_key)
                        kbd.release_all()
                    else:  # press a single key
                        kbd.press(macro_key)
                        kbd.release_all()
                    time.sleep(0.1)  # delay between keys
            else:  # press a single key
                kbd.press(key)
                kbd.release_all()
            time.sleep(0.1)  # debounce delay

    time.sleep(0.1)
