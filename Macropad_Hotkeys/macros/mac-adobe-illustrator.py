# MACROPAD Hotkeys example: Adobe Illustrator for Mac

from adafruit_hid.keycode import Keycode # REQUIRED if using Keycode.* values

app = {                         # REQUIRED dict, must be named 'app'
    'name' : 'Mac Illustrator', # Application name
    'macros' : [                # List of button macros...
        # COLOR    LABEL    KEY SEQUENCE
        # 1st row ----------
        (0x004000, 'Undo', [Keycode.COMMAND, 'z']),
        (0x004000, 'Redo', [Keycode.COMMAND, 'Z']),
        (0x303000, 'Pen', 'p'),     # Path-drawing tool
        # 2nd row ----------

        (0x101010, 'Select', 'v'),  # Select (path)
        (0x400000, 'Reflect', 'o'), # Reflect selection
        (0x303000, 'Rect', 'm'),    # Draw rectangle
        # 3rd row ----------
        (0x101010, 'Direct', 'a'),  # Direct (point) selection
        (0x400000, 'Rotate', 'r'),  # Rotate selection
        (0x303000, 'Oval', 'l'),    # Draw ellipse
        # 4th row ----------
        (0x101010, 'Eyedrop', 'i'), # Cycle eyedropper/measure modes
        (0x400000, 'Scale', 's'),   # Scale selection
        (0x303000, 'Text', 't'),    # Type tool
        # Encoder button ---
        (0x000000, '', [Keycode.COMMAND, Keycode.OPTION, 'S']) # Save for web
    ]
}
