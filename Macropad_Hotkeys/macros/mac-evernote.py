# MACROPAD Hotkeys: Evernote web application for Mac
# Contributed by Redditor s010sdc

from adafruit_hid.keycode import Keycode # REQUIRED if using Keycode.* values

app = {                      # REQUIRED dict, must be named 'app'
    'name' : 'Mac Evernote', # Application name
    'macros' : [             # List of button macros...
        # COLOR    LABEL    KEY SEQUENCE
        # 1st row ----------
        (0x004000, 'New Nt', [Keycode.COMMAND, 'n']),
        (0x004000, 'New Bk', [Keycode.SHIFT, Keycode.COMMAND, 'n']),
        (0x004000, 'CP Lnk', [Keycode.CONTROL, Keycode.OPTION, Keycode.COMMAND, 'c']),
        # 2nd row ----------
        (0x004000, 'Move', [Keycode.CONTROL, Keycode.COMMAND, 'm']),
        (0x004000, 'Find', [Keycode.OPTION, Keycode.COMMAND, 'f']),
        (0x004000, 'Emoji', [Keycode.CONTROL, Keycode.COMMAND, ' ']),
        # 3rd row ----------
        (0x004000, 'Bullets', [Keycode.SHIFT, Keycode.COMMAND, 'u']),
        (0x004000, 'Nums', [Keycode.SHIFT, Keycode.COMMAND, 'o']),
        (0x004000, 'Check', [Keycode.SHIFT, Keycode.COMMAND, 't']),
        # 4th row ----------
        (0x004000, 'Date', [Keycode.SHIFT, Keycode.COMMAND, 'D' ]),
        (0x004000, 'Time', [Keycode.OPTION, Keycode.SHIFT, Keycode.COMMAND, 'D' ]),
        (0x004000, 'Divider', [Keycode.SHIFT, Keycode.COMMAND, 'H']),
        # Encoder button ---
        (0x000000, '', [Keycode.COMMAND, 'w']) # Close window/tab
    ]
}
