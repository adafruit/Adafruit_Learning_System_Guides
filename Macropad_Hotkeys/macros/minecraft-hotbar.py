# MACROPAD Hotkeys example: Minecraft hotbar (inventory)

# Note: Must enable "full keyboad gameplay" for Prev/Next buttons to work.
#       This is found under "settings", then "keyboard and mouse".

from adafruit_hid.keycode import Keycode # REQUIRED if using Keycode.* values

app = {                          # REQUIRED dict, must be named 'app'
    'name' : 'Minecraft Hotbar', # Application name
    'macros' : [                 # List of button macros...
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
        (0x002020, 'Prev', [Keycode.PAGE_UP]),
        (0x000000, '', []),
        (0x002020, 'Next', [Keycode.PAGE_DOWN]),
        # Encoder button ---
        (0x000000, '', [])
    ]
}
