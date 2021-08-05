"""
A Python dictionary containing information to be associated with the twelve keys on a
MacroPad.
"""
from adafruit_macropad import MacroPad
macropad = MacroPad()
"""
** Understanding the Dictionary **
The following explains how to configure each entry below.

Sound:
Can be an integer for a tone in Hz, e.g.196, OR, a string for a wav file name, e.g. "cat.wav".

Label:
The label you would like to appear on the display. Should be limited to 6 characters to fit.

Keycode type:
You must update this to match the type of key sequence you're sending.
KC = Keycode
CC = ConsumerControlCode

Key sequence:
The Keycode, sequence of Keycodes, or ConsumerControlCode to send.
"""
shortcut_keys = {
    'macros': [
        # (Sound, Label, Keycode type, Key sequence)
        # 1st row ----------
        (196, 'Esc', 'KC', [macropad.Keycode.ESCAPE]),
        (220, 'Tab', 'KC', [macropad.Keycode.TAB]),
        (246, 'Vol+', 'CC', [macropad.ConsumerControlCode.VOLUME_INCREMENT]),
        # 2nd row ----------
        (262, 'Play', 'CC', [macropad.ConsumerControlCode.PLAY_PAUSE]),
        (294, 'Home', 'KC', [macropad.Keycode.HOME]),
        (330, 'Vol-', 'CC', [macropad.ConsumerControlCode.VOLUME_DECREMENT]),
        # 3rd row ----------
        (349, 'End', 'KC', [macropad.Keycode.END]),
        (392, 'Copy', 'KC', [macropad.Keycode.COMMAND, macropad.Keycode.C]),
        (440, 'Pg Up', 'KC', [macropad.Keycode.PAGE_UP]),
        # 4th row ----------
        (494, 'Quit', 'KC', [macropad.Keycode.COMMAND, macropad.Keycode.Q]),
        (523, 'Paste', 'KC', [macropad.Keycode.COMMAND, macropad.Keycode.V]),
        (587, 'Pg Dn', 'KC', [macropad.Keycode.PAGE_DOWN]),
    ]
}
