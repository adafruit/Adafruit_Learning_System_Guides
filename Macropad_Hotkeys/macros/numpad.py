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
        (0x200020, '7', [Keycode.KEYPAD_SEVEN]),
        (0x200020, '8', [Keycode.KEYPAD_EIGHT]),
        (0x200020, '9', [Keycode.KEYPAD_NINE]),
        # 2nd row ----------
        (0x200020, '4', [Keycode.KEYPAD_FOUR]),
        (0x200020, '5', [Keycode.KEYPAD_FIVE]),
        (0x200020, '6', [Keycode.KEYPAD_SIX]),
        # 3rd row ----------
        (0x200020, '1', [Keycode.KEYPAD_ONE]),
        (0x200020, '2', [Keycode.KEYPAD_TWO]),
        (0x200020, '3', [Keycode.KEYPAD_THREE]),
        # 4th row ----------
        (0x200010, '0', [Keycode.KEYPAD_ZERO]),
        (0x200010, '', [Keycode.KEYPAD_ZERO]),
        (0x000020, '.', [Keycode.KEYPAD_PERIOD]),
        # Encoder button ---
        (0x000000, '', [Keycode.BACKSPACE])
    ]
}
