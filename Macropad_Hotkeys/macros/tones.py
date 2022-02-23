# SPDX-FileCopyrightText: 2021 Phillip Burgess for Adafruit Industries
#
# SPDX-License-Identifier: MIT

# MACROPAD Hotkeys example: Tones

# The syntax for Tones in macros is highly peculiar, in order to maintain
# backward compatibility with the original keycode-only macro files.
# The third item for each macro is a list in brackets, and each value within
# is normally an integer (Keycode), float (delay) or string (typed literally).
# Consumer Control codes were added as list-within-list, and then mouse and
# tone further complicate this by adding dicts-within-list. Each tone-related
# item is the key 'tone' with either an integer frequency value, or 0 to stop
# the tone mid-macro (tone is also stopped when key is released).
# Helpful: https://en.wikipedia.org/wiki/Piano_key_frequencies

# This example ONLY shows tones (and delays), but really they can be mixed
# with other elements (keys, codes, mouse) to provide auditory feedback.

app = {               # REQUIRED dict, must be named 'app'
    'name' : 'Tones', # Application name
    'macros' : [      # List of button macros...
        # COLOR    LABEL    KEY SEQUENCE
        # 1st row ----------
        (0x200000, 'C3', [{'tone':131}]),
        (0x202000, 'C4', [{'tone':262}]),
        (0x002000, 'C5', [{'tone':523}]),
        # 2nd row ----------
        (0x000020, 'Rising', [{'tone':131}, 0.2, {'tone':262}, 0.2, {'tone':523}]),
        (0x000000, '', []),
        (0x000020, 'Falling', [{'tone':523}, 0.2, {'tone':262}, 0.2, {'tone':131}]),
        # 3rd row ----------
        (0x000000, '', []),
        (0x000000, '', []),
        (0x000000, '', []),
        # 4th row ----------
        (0x000000, '', []),
        (0x000000, '', []),
        (0x000000, '', []),
        # Encoder button ---
        (0x000000, '', [])
    ]
}
