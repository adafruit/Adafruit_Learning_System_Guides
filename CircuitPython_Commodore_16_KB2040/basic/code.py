# SPDX-FileCopyrightText: 2022 Jeff Epler for Adafruit Industries
# SPDX-License-Identifier: MIT

# Commodore 16 to USB HID adapter with Adafruit KB2040
#
# Note that:
#  * This matrix is different than the (more common) Commodore 64 matrix
#  * There are no diodes, not even on modifiers, so there's only 2-key rollover.
#  * This is a "physical" keymap, so that the functions of the keys are similar to the
#    function of a standard PC keyboard key in the same location.
#
# See the guide or the advanced code for more information about the key matrix

import board
import keypad
from adafruit_hid.keycode import Keycode as K
from adafruit_hid.keyboard import Keyboard
import usb_hid

rows = [board.A3, board.D6, board.D10, board.D9, board.MOSI, board.D2, board.A0, board.D4]
cols = [board.A2, board.SCK, board.MISO, board.A1, board.D5, board.D7, board.D8, board.D3]

keycodes = [
    K.BACKSPACE, K.ENTER, K.LEFT_ARROW, K.F8, K.F1, K.F2, K.F3, K.LEFT_BRACKET,
    K.THREE, K.W, K.A, K.FOUR, K.Z, K.S, K.E, K.LEFT_SHIFT,
    K.FIVE, K.R, K.D, K.SIX, K.C, K.F, K.T, K.X,
    K.SEVEN, K.Y, K.G, K.EIGHT, K.B, K.H, K.U, K.V,
    K.NINE, K.I, K.J, K.ZERO, K.M, K.K, K.O, K.N,
    K.DOWN_ARROW, K.P, K.L, K.UP_ARROW, K.PERIOD, K.SEMICOLON, K.BACKSLASH, K.COMMA,
    K.MINUS, K.KEYPAD_ASTERISK, K.QUOTE, K.EQUALS, K.ESCAPE, K.RIGHT_ARROW, K.RIGHT_BRACKET,
    K.FORWARD_SLASH, K.ONE, K.HOME, K.LEFT_CONTROL, K.TWO, K.SPACE, K.ALT, K.Q, K.GRAVE_ACCENT,
]

kbd = Keyboard(usb_hid.devices)

with keypad.KeyMatrix(rows, cols) as keys:
    while True:
        if ev := keys.events.get():
            keycode = keycodes[ev.key_number]
            if ev.pressed:
                kbd.press(keycode)
            else:
                kbd.release(keycode)
