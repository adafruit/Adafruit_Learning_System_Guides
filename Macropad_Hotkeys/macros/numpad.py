# SPDX-FileCopyrightText: 2021 Emma Humphries for Adafruit Industries
#
# SPDX-License-Identifier: MIT

# MACROPAD Hotkeys example: Universal Numpad

from adafruit_hid.keycode import Keycode # REQUIRED if using Keycode.* values

app = {                # REQUIRED dict, must be named 'app'
    'name' : 'Numpad', # Application name
    'macros' : [       # List of button macros...
        # COLOR    LABEL    KEY SEQUENCE
        # 1st row ----------
        (0x202000, '7', ['7']),
        (0x202000, '8', ['8']),
        (0x202000, '9', ['9']),
        # 2nd row ----------
        (0x202000, '4', ['4']),
        (0x202000, '5', ['5']),
        (0x202000, '6', ['6']),
        # 3rd row ----------
        (0x202000, '1', ['1']),
        (0x202000, '2', ['2']),
        (0x202000, '3', ['3']),
        # 4th row ----------
        (0x101010, '*', ['*']),
        (0x800000, '0', ['0']),
        (0x101010, '#', ['#']),
        # Encoder button ---
        (0x000000, '', [Keycode.BACKSPACE])
    ]
}
