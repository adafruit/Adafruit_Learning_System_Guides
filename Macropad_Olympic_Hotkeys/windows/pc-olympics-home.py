# SPDX-FileCopyrightText: 2021 Isaac Wellish for Adafruit Industries
#
# SPDX-License-Identifier: MIT

# MACROPAD Olympic Hotkeys main page
# pylint: disable=line-too-long

from adafruit_hid.keycode import Keycode # REQUIRED if using Keycode.* values

app = {                # REQUIRED dict, must be named 'app'
    'name' : 'Olympics Home', # Application name
    'macros' : [       # List of button macros...
        # COLOR    LABEL    KEY SEQUENCE
        # 1st row ----------
        (0x004000, '< Tab', [Keycode.CONTROL, Keycode.SHIFT, Keycode.TAB]),
        (0x004000, 'Tab >', [Keycode.CONTROL, Keycode.TAB]),
        (0x400000, 'Up', [Keycode.SHIFT, ' ']),      # Scroll up
        # 2nd row ----------
        # Full schedule in new tab
        (0x3F3F3F, 'Sched', [Keycode.CONTROL, 't', -Keycode.CONTROL,
                             'https://olympics.com/tokyo-2020/olympic-games/en/results/all-sports/olympic-schedule.htm\n']),
        # Medal standings in new tab
        (0x404000 , 'Medals', [Keycode.CONTROL, 't', -Keycode.CONTROL,
                               'https://olympics.com/tokyo-2020/olympic-games/en/results/all-sports/medal-standings.htm\n']),
        (0x400000, 'Down', ' '),     # Scroll down
        # 3rd row ----------
        # Peacock streaming service Olympics home in new tab
        (0x000040, 'PC', [Keycode.CONTROL, 't', -Keycode.CONTROL,
                          'https://www.peacocktv.com/watch/2020-tokyo-olympics\n']),
        # Full schedule in new tab
        (0x000040, 'NBC', [Keycode.CONTROL, 't', -Keycode.CONTROL,
                           'https://www.usanetwork.com/live?brand=cnbc&callsign=nbc\n']),
        # Medal standings in new tab
        (0x000040 , 'YT', [Keycode.CONTROL, 't', -Keycode.CONTROL,
                           'https://www.youtube.com/channel/UCTl3QQTvqHFjurroKxexy2Q\n']),
        # 4th row ----------
        # NBC in new tab
        (0x000040, 'CNBC', [Keycode.CONTROL, 't', -Keycode.CONTROL,
                            'https://www.usanetwork.com/live?brand=nbc&callsign=cnbc\n']),
        # USA in new tab
        (0x000040, 'USA', [Keycode.CONTROL, 't', -Keycode.CONTROL,
                           'https://www.usanetwork.com/live?brand=usa&callsign=usa_east\n']),
        # NBCSN in new tab
        (0x000040, 'NBCSN', [Keycode.CONTROL, 't', -Keycode.CONTROL,
                             'https://www.usanetwork.com/live?brand=nbc-sports&callsign=nbcsn\n']),
        # Encoder button ---
        (0x000000, '', [Keycode.CONTROL, 'w']) # Close window/tab
    ]
}
