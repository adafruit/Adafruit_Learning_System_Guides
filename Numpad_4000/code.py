# SPDX-FileCopyrightText: 2021 John Park for Adafruit Industries
# SPDX-License-Identifier: MIT
# NUMPAD 4000! Made with snap-apart NeoKey PCB and Feather RP2040.

import board
import keypad
import neopixel
import usb_hid
from adafruit_hid.keyboard import Keyboard
from adafruit_hid.keycode import Keycode

COLUMNS = 5
ROWS = 5

BLUE = 0x000510
WHITE = 0x303030
RED = 0xFF0000


board_pix = neopixel.NeoPixel(board.NEOPIXEL, 1, brightness=0.1)
board_pix[0] = BLUE

key_pixels = neopixel.NeoPixel(board.D5, 30, brightness=0.1)
key_pixels.fill(WHITE)

keys = keypad.KeyMatrix(
    row_pins=(board.D4, board.A3, board.A2, board.A1, board.A0),
    column_pins=(board.D13, board.D12, board.D11, board.D10, board.D9),
    columns_to_anodes=False,
)

kbd = Keyboard(usb_hid.devices)

keycode_LUT = [
             0, 1, 2, 3, 4,
             5, 6, 7, 8,
             10, 11, 12, 13, 14,
             15, 16, 17, 18,
             20, 21, 23, 24
]

pixel_LUT = [
             0, 1, 2, 3, 4,
             8, 7, 6, 5,
             10, 11, 12, 13, 14,
             18, 17, 16, 15,
             20, 21, 23, 24
]
# create a keycode dictionary including modifier state and keycodes
keymap = {
            (0): (0, Keycode.KEYPAD_NUMLOCK),
            (1): (0, Keycode.BACKSPACE),
            (2): (0, Keycode.FORWARD_SLASH),
            (3): (0, Keycode.KEYPAD_ASTERISK),
            (4): (0, Keycode.KEYPAD_MINUS),

            (5): (0, Keycode.PAGE_UP),
            (6): (0, Keycode.KEYPAD_SEVEN),
            (7): (0, Keycode.KEYPAD_EIGHT),
            (8): (0, Keycode.KEYPAD_NINE),

            (9): (0, Keycode.PAGE_DOWN),
            (10): (0, Keycode.KEYPAD_FOUR),
            (11): (0, Keycode.KEYPAD_FIVE),
            (12): (0, Keycode.KEYPAD_SIX),
            (13): (0, Keycode.KEYPAD_PLUS),

            (14): (1, Keycode.SHIFT),
            (15): (0, Keycode.KEYPAD_ONE),
            (16): (0, Keycode.KEYPAD_TWO),
            (17): (0, Keycode.KEYPAD_THREE),

            (18): (2, Keycode.CONTROL),
            (19): (0, Keycode.KEYPAD_ZERO),
            (20): (0, Keycode.KEYPAD_PERIOD),
            (21): (0, Keycode.KEYPAD_EQUALS)  # KEYPAD_ENTER on non-mac
}

shift_mod = False
ctrl_mod = False


while True:

    key_event = keys.events.get()
    if key_event:
        if key_event.pressed:
            if keymap[keycode_LUT.index(key_event.key_number)][0] == 1:
                shift_mod = True
            elif keymap[keycode_LUT.index(key_event.key_number)][0] == 2:
                ctrl_mod = True
            if shift_mod is False and ctrl_mod is False:
                kbd.press(keymap[keycode_LUT.index(key_event.key_number)][1])
                print(keymap[keycode_LUT.index(key_event.key_number)][1])
                key_pixels[pixel_LUT.index(key_event.key_number)] = RED
            elif shift_mod is True and ctrl_mod is False:
                kbd.press(Keycode.SHIFT, keymap[keycode_LUT.index(key_event.key_number)][1])
                print(keymap[keycode_LUT.index(key_event.key_number)][1])
                key_pixels[pixel_LUT.index(key_event.key_number)] = RED
            elif shift_mod is False and ctrl_mod is True:
                kbd.press(Keycode.CONTROL, keymap[keycode_LUT.index(key_event.key_number)][1])
                print(keymap[keycode_LUT.index(key_event.key_number)][1])
                key_pixels[pixel_LUT.index(key_event.key_number)] = RED
            elif shift_mod is True and ctrl_mod is True:
                kbd.press(
                          Keycode.SHIFT,
                          Keycode.CONTROL,
                          keymap[keycode_LUT.index(key_event.key_number)][1]
                          )
                print(keymap[keycode_LUT.index(key_event.key_number)][1])
                key_pixels[pixel_LUT.index(key_event.key_number)] = RED
            board_pix[0] = WHITE

        if key_event.released:
            if keymap[keycode_LUT.index(key_event.key_number)][0] == 1:  # un-shift
                shift_mod = False
            elif keymap[keycode_LUT.index(key_event.key_number)][0] == 2:  # un-ctrl
                ctrl_mod = False

            kbd.release(keymap[keycode_LUT.index(key_event.key_number)][1])
            key_pixels[pixel_LUT.index(key_event.key_number)] = WHITE
            board_pix[0] = BLUE
