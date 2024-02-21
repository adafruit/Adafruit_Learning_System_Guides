# SPDX-FileCopyrightText: 2020 John Park for Adafruit Industries
#
# SPDX-License-Identifier: MIT

# ItsyBitsy Keypad
# Uses ItsyBitsy M4/M0 plus Pimoroni Keybow
# To build a customizable USB keypad

import time
import board
from digitalio import DigitalInOut, Direction, Pull
import usb_hid
from adafruit_hid.keyboard import Keyboard
from adafruit_hid.keycode import Keycode
from adafruit_hid.consumer_control import ConsumerControl
from adafruit_hid.consumer_control_code import ConsumerControlCode
import adafruit_dotstar as dotstar

dots = dotstar.DotStar(board.SCK, board.MOSI, 12, brightness=0.4)

RED = 0xFF0000
AMBER = 0xAA9900
BLUE = 0x0066FF
MAGENTA = 0xFF00FF
PURPLE = 0x3B0F85
BLACK = 0x000000

kbd = Keyboard(usb_hid.devices)
cc = ConsumerControl(usb_hid.devices)

orientation = 1  # 0 = portrait/vertical, 1 = landscape/horizontal
if orientation == 0:
    key_dots = [0, 4, 8, 1, 5, 9, 2, 6, 10, 3, 7, 11]
    # 0  #4  #8
    # 1  #5  #9
    # 2  #6  #10
    # 3  #7  #11
if orientation == 1:
    key_dots = [3, 2, 1, 0, 7, 6, 5, 4, 11, 10, 9, 8]
    # 3  #2  #1  #0
    # 7  #6  #5  #4
    # 11 #10 #9  #8


def dot_on(dot, color):
    dots[dot] = color


def dot_off(dot):
    dots[dot] = BLACK


# Pin definitions
if orientation == 0:  # 0 = portrait/vertical
    pins = [
        board.D11,
        board.D12,
        board.D2,
        board.D10,
        board.D9,
        board.D7,
        board.A5,
        board.A4,
        board.A3,
        board.A2,
        board.A1,
        board.A0,
    ]
if orientation == 1:  # 1 = landscape/horizontal
    pins = [
        board.A2,
        board.A5,
        board.D10,
        board.D11,
        board.A1,
        board.A4,
        board.D9,
        board.D12,
        board.A0,
        board.A3,
        board.D7,
        board.D2,
    ]
# the two command types -- MEDIA for ConsumerControlCodes, KEY for Keycodes
# this allows button press to send the correct HID command for the type specified
MEDIA = 1
KEY = 2
keymap = {
    (0): (AMBER, MEDIA, ConsumerControlCode.PLAY_PAUSE),
    (1): (AMBER, MEDIA, ConsumerControlCode.MUTE),
    (2): (AMBER, MEDIA, ConsumerControlCode.VOLUME_DECREMENT),
    (3): (AMBER, MEDIA, ConsumerControlCode.VOLUME_INCREMENT),
    (4): (BLUE, KEY, (Keycode.GUI, Keycode.C)),
    (5): (BLUE, KEY, (Keycode.GUI, Keycode.V)),
    (6): (MAGENTA, KEY, [Keycode.UP_ARROW]),
    (7): (PURPLE, KEY, [Keycode.BACKSPACE]),
    (8): (BLUE, KEY, [Keycode.SPACE]),
    (9): (MAGENTA, KEY, [Keycode.LEFT_ARROW]),
    (10): (MAGENTA, KEY, [Keycode.DOWN_ARROW]),
    (11): (MAGENTA, KEY, [Keycode.RIGHT_ARROW]),
}

switches = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11]
for i in range(12):
    switches[i] = DigitalInOut(pins[i])
    switches[i].direction = Direction.INPUT
    switches[i].pull = Pull.UP

switch_state = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]

print("ItsyBitsy Keybow")

# Starup lights
for k in range(12):
    dot_on(key_dots[k], RED)
    time.sleep(0.05)
    dot_on(key_dots[k], keymap[k][0])  # use individual key colors from set
    time.sleep(0.05)

while True:
    for button in range(12):
        if switch_state[button] == 0:
            if not switches[button].value:
                try:
                    if keymap[button][1] == KEY:
                        kbd.press(*keymap[button][2])
                    else:
                        cc.send(keymap[button][2])
                    dot_on(key_dots[button], RED)
                except ValueError:  # deals w six key limit
                    pass
                print("pressed key{}".format(button))
                switch_state[button] = 1

        if switch_state[button] == 1:
            if switches[button].value:
                try:
                    if keymap[button][1] == KEY:
                        kbd.release(*keymap[button][2])
                    dot_on(key_dots[button], keymap[button][0])
                except ValueError:
                    pass
                print("released key{}".format(button))
                switch_state[button] = 0

    time.sleep(0.01)  # debounce
