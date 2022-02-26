# MACROPAD Hotkeys example: MIDI

# The syntax for MIDI is based off of Tones in macros, in order to maintain
# backward compatibility with the original keycode-only macro files.
# The third item for each macro is a list in brackets, and each value within
# is normally an integer (Keycode), float (delay) or string (typed literally).
# Consumer Control codes were added as list-within-list, and then mouse and
# tone and midinote further complicate this by adding dicts-within-list. Each
# midinote related item is the key 'midinote' with an integer  value between
# 0 and 127 as per the MIDI spec.
# Unlike the Tone macro the midinote is momentarily played and also stopped
# once for keypress.  This is useful for triggering functions within a DAW.
# (but less useful for playing in instrument directly)
#
# The midicc syntax further complicates the syntax by taking a list within
# brackets containing a CC number and a value between 0 and 127 as per the
# MIDI spec.

# Helpful: https://en.wikipedia.org/wiki/Piano_key_frequencies

# This example ONLY shows midinote and midicc, but really they can be mixed
# with other elements (keys, codes, mouse) to provide auditory feedback.

app = {               # REQUIRED dict, must be named 'app'
    'name' : 'MIDI', # Application name
    'macros' : [      # List of button macros...
        # COLOR    LABEL    KEY SEQUENCE
        # 1st row ----------
        (0x200005, 'C4', [{'midinote':48}]),
        (0x200005, 'D4', [{'midinote':50}]),
        (0x200005, 'E4', [{'midinote':52}]),
        # 2nd row ----------
        (0x000000, '', []),
        (0x000000, '', []),
        (0x000000, '', []),
        # 3rd row ----------
        (0x000000, '', []),
        (0x000000, '', []),
        (0x000000, '', []),
        # 4th row ----------
	(0x050000, 'Vol 40', [{'midicc':[7,40]}]),
        (0x100000, 'Vol 90', [{'midicc':[7,90]}]),
        (0x200000, 'Vol127', [{'midicc':[7,127]}]),
        # Encoder button ---
        (0x000000, '', [])
    ]
}
