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

# define buttons
num_keys = 4
pins = (
    board.GP0,
    board.GP1,
    board.GP2,
    board.GP3
)

keys = []
for pin in pins:
    tmp_pin = DigitalInOut(pin)
    tmp_pin.pull = Pull.UP
    keys.append(Debouncer(tmp_pin))

keymap = {
    (0): ("Select all", [Keycode.GUI, Keycode.A]),
    (1): ("Cut", [Keycode.GUI, Keycode.X]),
    (2): ("Copy", [Keycode.GUI, Keycode.C]),
    (3): ("Paste", [Keycode.GUI, Keycode.V])
}

print("\nWelcome to keypad")
print("keymap:")
for k in range(num_keys):
    print("\t", (keymap[k][0]))


while True:
    for i in range(num_keys):
        keys[i].update()
        if keys[i].fell:
            print(keymap[i][0])
            kpd.send(*keymap[i][1])
