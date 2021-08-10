# SPDX-FileCopyrightText: Copyright (c) 2021 Dylan Herrada for Adafruit Industries
#
# SPDX-License-Identifier: Unlicense
import time
import usb_hid
from adafruit_hid.keyboard import Keyboard
from adafruit_hid.keyboard_layout_us import KeyboardLayoutUS
import adafruit_ducky

time.sleep(1)  # Sleep for a bit to avoid a race condition on some systems
keyboard = Keyboard(usb_hid.devices)
keyboard_layout = KeyboardLayoutUS(keyboard)  # We're in the US :)

duck = adafruit_ducky.Ducky("duckyscript.txt", keyboard, keyboard_layout)

result = True
while result is not False:
    result = duck.loop()
