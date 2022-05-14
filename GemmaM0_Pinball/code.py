# SPDX-FileCopyrightText: 2022 john park & tod kurt for Adafruit Industries
# SPDX-License-Identifier: MIT
# Gemma IO demo - Keyboard emu
# iCade Pinball Edition

import board
from digitalio import DigitalInOut, Pull
from adafruit_debouncer import Debouncer
import usb_hid
from adafruit_hid.keyboard import Keyboard
from adafruit_hid.keycode import Keycode

# Allows three buttons on a Gemma M0 to control iCade standard Pinball Arcade
# game on iOS using USB to Lightning "camera connector"

# iCade keyboard mappings
# See developer doc at: http://www.ionaudio.com/products/details/icade

#    WE     YT UF IM OG
# AQ< -->DC
#    XZ     HR JN KP LV

#control key is triggered by a press, doesn't repeat, second control key is
#triggered by a release

# define buttons
num_keys = 3
pins = (
    board.D0, # D0
    board.D1, # D1
    board.D2 # D2
)

keys = []

# The keycode pair sent for each button:
# D0 is left flipper -  iCade key sequence (hold, release) is "hr"
# D1 is right flipper - iCade key sequence (hold, release) is "lv"
# D2 is plunger -       iCade key sequence (hold, release) is "xz"

for pin in pins:
    tmp_pin = DigitalInOut(pin)
    tmp_pin.pull = Pull.UP
    keys.append(Debouncer(tmp_pin))

keymap_pressed = {
    (0): ("Left Paddle", [Keycode.H]),
    (1): ("Right Paddle", [Keycode.L]),
    (2): ("Plunger", [Keycode.X])
}
keymap_released = {
    (0): ("Left Paddle", [Keycode.R]),
    (1): ("Right Paddle", [Keycode.V]),
    (2): ("Plunger", [Keycode.Z])
}

# the keyboard object
kbd = Keyboard(usb_hid.devices)

print("\nWelcome to keypad")
print("keymap:")
for k in range(num_keys):
    print("\t", (keymap_pressed[k][0]))
print("Waiting for button presses")


while True:
    for i in range(num_keys):
        keys[i].update()
        if keys[i].fell:
            print(keymap_pressed[i][0])
            kbd.send(*keymap_pressed[i][1])
        if keys[i].rose:
            print(keymap_released[i][0])
            kbd.send(*keymap_released[i][1])
