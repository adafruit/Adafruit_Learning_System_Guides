# SPDX-FileCopyrightText: 2021 john park for Adafruit Industries
# SPDX-License-Identifier: MIT
# Pico Four Key USB HID Keypad

import board
from digitalio import DigitalInOut, Pull
from adafruit_debouncer import Debouncer
import usb_hid
from adafruit_hid.keyboard import Keyboard
from adafruit_hid.keycode import Keycode

kpd = Keyboard(usb_hid.devices)

# Choose the correct modifier key for Windows or Mac.
# Comment one line and uncomment the other.
# MODIFIER = Keycode.CONTROL  # For Windows
MODIFIER = Keycode.COMMAND  # For Mac

# define buttons
NUM_KEYS = 4
PINS = (
    board.GP0,
    board.GP1,
    board.GP2,
    board.GP3,
)

KEYMAP = (
    ("Select all", [MODIFIER, Keycode.A]),
    ("Cut", [MODIFIER, Keycode.X]),
    ("Copy", [MODIFIER, Keycode.C]),
    ("Paste", [MODIFIER, Keycode.V]),
)

keys = []
for pin in PINS:
    dio = DigitalInOut(pin)
    dio.pull = Pull.UP
    keys.append(Debouncer(dio))

print("\nWelcome to keypad")
print("keymap:")
for k in range(NUM_KEYS):
    print("\t", (KEYMAP[k][0]))


while True:
    for i in range(NUM_KEYS):
        keys[i].update()
        if keys[i].fell:
            print(KEYMAP[i][0])
            kpd.send(*KEYMAP[i][1])
