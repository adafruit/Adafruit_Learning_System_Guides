# SPDX-FileCopyrightText: 2021 Victor Toni - GitHub @vitoni
#
# SPDX-License-Identifier: MIT

# MACROPAD Hotkeys example: blank screen for idle


app = {                      # REQUIRED dict, must be named 'app'
    'name' : '',             # Application name
    'macros' : [             # List of button macros...
        # COLOR    LABEL    KEY SEQUENCE
        # 1st row ----------
        (0x000000, '',          []),
        (0x000000, '',          []),
        (0x000000, '',          []),
        # 2nd row ----------
        (0x000000, '',          []),
        (0x000000, '',          []),
        (0x000000, '',          []),
        # 3rd row ----------
        (0x000000, '',          []),
        (0x000000, '',          []),
        (0x000000, '',          []),
        # 4th row ----------
        (0x000000, '',          []),
        (0x000000, '',          []),
        (0x000000, '',          []),
        # Encoder button ---
        (0x000000, '',          [])
    ]
}
