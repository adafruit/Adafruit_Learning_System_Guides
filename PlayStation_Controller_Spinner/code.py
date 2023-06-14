# SPDX-FileCopyrightText: 2023 John Park w/ Tod Kurt ps2controller library
#
# SPDX-License-Identifier: MIT
# The Takara Game of Life PlayStation roulette wheel controller spinner
# sends two sets of held CIRCLE buttons with randomized hold time periods
# this code turns that into mouse click spamming (the CIRCLE button also spams)

import time
import board
import usb_hid
import digitalio
from adafruit_hid.keycode import Keycode
from adafruit_hid.keyboard import Keyboard
from adafruit_hid.keyboard_layout_us import KeyboardLayoutUS
from adafruit_hid.mouse import Mouse
from ps2controller import PS2Controller

# turn on Pico LED
led = digitalio.DigitalInOut(board.GP25)
led.direction = digitalio.Direction.OUTPUT
led.value = True

mouse = Mouse(usb_hid.devices)

keyboard = Keyboard(usb_hid.devices)
layout = KeyboardLayoutUS(keyboard)

# create controller object with Pico wiring, disable unused PS2 features
psx = PS2Controller(
    dat=board.GP2,
    cmd=board.GP3,
    att=board.GP4,
    clk=board.GP5,
    enable_sticks=False,
    enable_rumble=False,
    enable_pressure=False,
)

circle_held = False
spam_speed = 0.001

buttonmap = {
            ("SELECT"): (0, Keycode.SPACEBAR),
            ("START"): (0, Keycode.X),
            ("UP"): (0, Keycode.W),
            ("DOWN"): (0, Keycode.S),
            ("RIGHT"): (0, Keycode.D),
            ("LEFT"): (0, Keycode.A),
            ("L2"): (0, Keycode.R),
            ("R2"): (0, Keycode.T),
            ("L1"): (0, Keycode.F),
            ("R1"): (0, Keycode.G),
            ("TRIANGLE"): (0, Keycode.I),
            ("CIRCLE"): (1, Mouse.LEFT_BUTTON),  # for mouse clicks
            ("CROSS"): (0, Keycode.K),
            ("SQUARE"): (0, Keycode.L),
}

print("PlayStation Roulette Wheel controller")

while True:
    events = psx.update()
    if events:
        print("events", events)
        for event in events:
            if buttonmap[event.name][0] == 0:  # regular button
                if event.pressed:
                    keyboard.press(buttonmap[event.name][1])
                if event.released:
                    keyboard.release(buttonmap[event.name][1])

            if buttonmap[event.name][0] == 1:  # mouse button
                if event.pressed:
                    circle_held = True
                if event.released:
                    circle_held = False

    if circle_held:  # spam the mouse click
        mouse.press(buttonmap["CIRCLE"][1])
        mouse.release_all()
        time.sleep(spam_speed)
