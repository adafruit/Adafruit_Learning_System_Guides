# MACROPAD Hotkeys example: Minecraft Messaging

# NOTE: There appears to be a line length limit. Exceeding that limit appears
#       to result in silent failure.  Therefore, the key sequences are split
#       across multiple lines.

from adafruit_hid.keycode import Keycode # REQUIRED if using Keycode.* values

DELAY_AFTER_ESCAPE = 0.05
DELAY_AFTER_COMMAND = 0.10

app = {                              # REQUIRED dict, must be named 'app'
    'name' : 'Minecraft (/msg)',     # Application name
    'macros' : [                     # List of button macros...
        # COLOR    LABEL    KEY SEQUENCE
        # 1st row ----------
        (0x000020, 'list', [
            Keycode.ESCAPE, -Keycode.ESCAPE,
            '/list',
            Keycode.RETURN, -Keycode.RETURN]),
        (0x000020, 'list', [
            Keycode.ESCAPE, -Keycode.ESCAPE,
            '/list',
            Keycode.RETURN, -Keycode.RETURN]),
        (0x000020, 'list', [
            Keycode.ESCAPE, -Keycode.ESCAPE,
            '/list',
            Keycode.RETURN, -Keycode.RETURN]),
        # 2nd row ----------
        (0x000000, '',     []),
        (0x000000, '',     []),
        (0x000000, '',     []),
        # 3rd row ----------
        (0x000000, '',     []),
        (0x000000, '',     []),
        (0x000000, '',     []),
        # 4th row ----------
        (0x101010, 'bed', [
            Keycode.ESCAPE, -Keycode.ESCAPE,
            '/msg @a Time for bed!',
            Keycode.RETURN, -Keycode.RETURN]),
        (0x101010, 'bed', [
            Keycode.ESCAPE, -Keycode.ESCAPE,
            '/msg @a Time for bed!',
            Keycode.RETURN, -Keycode.RETURN]),
        (0x101010, 'bed', [
            Keycode.ESCAPE, -Keycode.ESCAPE,
            '/msg @a Time for bed!',
            Keycode.RETURN, -Keycode.RETURN]),
        # Encoder button ---
        (0x000000, '', [])
    ]
}
