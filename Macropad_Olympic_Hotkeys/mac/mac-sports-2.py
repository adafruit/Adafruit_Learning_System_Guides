# MACROPAD Olympic Hotkeys sports page 2
# pylint: disable=line-too-long

from adafruit_hid.keycode import Keycode # REQUIRED if using Keycode.* values

app = {                # REQUIRED dict, must be named 'app'
    'name' : 'Sports 2', # Application name
    'macros' : [       # List of button macros...
        # COLOR    LABEL    KEY SEQUENCE
        # 1st row ----------
        (0x3F3F3F, 'BMX Fr', [Keycode.COMMAND, 't', -Keycode.COMMAND,
                              'https://olympics.com/tokyo-2020/olympic-games/en/results/cycling-bmx-freestyle/olympic-schedule-and-results.htm\n']),
        (0x400000, 'BMX Ra', [Keycode.COMMAND, 't', -Keycode.COMMAND,
                              'https://olympics.com/tokyo-2020/olympic-games/en/results/cycling-bmx-racing/olympic-schedule-and-results.htm\n']),
        (0x3F3F3F , 'Mtn Bk', [Keycode.COMMAND, 't', -Keycode.COMMAND,
                               'https://olympics.com/tokyo-2020/olympic-games/en/results/cycling-mountain-bike/olympic-schedule-and-results.htm\n']),
        # 2nd row ----------
        (0x400000, 'Cyc Rd', [Keycode.COMMAND, 't', -Keycode.COMMAND,
                              'https://olympics.com/tokyo-2020/olympic-games/en/results/cycling-road/olympic-schedule-and-results.htm\n']),
        (0x3F3F3F, 'Cyc Tr', [Keycode.COMMAND, 't', -Keycode.COMMAND,
                              'https://olympics.com/tokyo-2020/olympic-games/en/results/cycling-track/olympic-schedule-and-results.htm\n']),
        (0x000040 , 'Dive', [Keycode.COMMAND, 't', -Keycode.COMMAND,
                             'https://olympics.com/tokyo-2020/olympic-games/en/results/diving/olympic-schedule-and-results.htm\n']),
        # 3rd row ----------
        (0x3F3F3F, 'Equest', [Keycode.COMMAND, 't', -Keycode.COMMAND,
                              'https://olympics.com/tokyo-2020/olympic-games/en/results/equestrian/olympic-schedule-and-results.htm\n']),
        (0x000040, 'Fence', [Keycode.COMMAND, 't', -Keycode.COMMAND,
                             'https://olympics.com/tokyo-2020/olympic-games/en/results/fencing/olympic-schedule-and-results.htm\n']),
        (0x3F3F3F , 'Fball', [Keycode.COMMAND, 't', -Keycode.COMMAND,
                              'https://olympics.com/tokyo-2020/olympic-games/en/results/football/olympic-schedule-and-results.htm\n']),
        # 4th row ----------
        (0x404000, 'Golf', [Keycode.COMMAND, 't', -Keycode.COMMAND,
                            'https://olympics.com/tokyo-2020/olympic-games/en/results/golf/olympic-schedule-and-results.htm\n']),
        (0x3F3F3F, 'Hball', [Keycode.COMMAND, 't', -Keycode.COMMAND,
                             'https://olympics.com/tokyo-2020/olympic-games/en/results/handball/olympic-schedule-and-results.htm\n']),
        (0x404000, 'Hockey', [Keycode.COMMAND, 't', -Keycode.COMMAND,
                              'https://olympics.com/tokyo-2020/olympic-games/en/results/hockey/olympic-schedule-and-results.htm \n']),
        # Encoder button ---
        (0x000000, '', [Keycode.COMMAND, 'w']) # Close window/tab
    ]
}
