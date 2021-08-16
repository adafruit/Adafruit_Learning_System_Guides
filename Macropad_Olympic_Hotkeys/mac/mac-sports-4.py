# MACROPAD Olympic Hotkeys sports page 4
# pylint: disable=line-too-long

from adafruit_hid.keycode import Keycode # REQUIRED if using Keycode.* values

app = {                # REQUIRED dict, must be named 'app'
    'name' : 'Sports 4', # Application name
    'macros' : [       # List of button macros...
        # COLOR    LABEL    KEY SEQUENCE
        # 1st row ----------
        (0x3F3F3F, 'Swim', [Keycode.COMMAND, 't', -Keycode.COMMAND,
                            'https://olympics.com/tokyo-2020/olympic-games/en/results/swimming/olympic-schedule-and-results.htm\n']),
        (0x404000, 'TTennis', [Keycode.COMMAND, 't', -Keycode.COMMAND,
                               'https://olympics.com/tokyo-2020/olympic-games/en/results/table-tennis/olympic-schedule-and-results.htm\n']),
        (0x3F3F3F, 'Tkwndo', [Keycode.COMMAND, 't', -Keycode.COMMAND,
                              'https://olympics.com/tokyo-2020/olympic-games/en/results/Taekwondo/olympic-schedule-and-results.htm\n']),
        # 2nd row ----------
        (0x404000, 'Tennis', [Keycode.COMMAND, 't', -Keycode.COMMAND,
                              'https://olympics.com/tokyo-2020/olympic-games/en/results/tennis/olympic-schedule-and-results.htm\n']),
        (0x3F3F3F, 'TGym', [Keycode.COMMAND, 't', -Keycode.COMMAND,
                            'https://olympics.com/tokyo-2020/olympic-games/en/results/trampoline-gymnastics/olympic-schedule-and-results.htm\n']),
        (0x004000 , 'Trithln', [Keycode.COMMAND, 't', -Keycode.COMMAND,
                                'https://olympics.com/tokyo-2020/olympic-games/en/results/triathlon/olympic-schedule-and-results.htm\n']),
        # 3rd row ----------
        (0x3F3F3F, 'VBall', [Keycode.COMMAND, 't', -Keycode.COMMAND,
                             'https://olympics.com/tokyo-2020/olympic-games/en/results/volleyball/olympic-schedule-and-results.htm\n']),
        (0x004000, 'WPolo', [Keycode.COMMAND, 't', -Keycode.COMMAND,
                             'https://olympics.com/tokyo-2020/olympic-games/en/results/water-polo/olympic-schedule-and-results.htm\n']),
        (0x3F3F3F , 'Wlift', [Keycode.COMMAND, 't', -Keycode.COMMAND,
                              'https://olympics.com/tokyo-2020/olympic-games/en/results/weightlifting/olympic-schedule-and-results.htm\n']),
        # 4th row ----------
        (0x400000, 'Wrestl', [Keycode.COMMAND, 't', -Keycode.COMMAND,
                              'https://olympics.com/tokyo-2020/olympic-games/en/results/wrestling/olympic-schedule-and-results.htm\n']),
        (0x3F3F3F, '', [Keycode.COMMAND, 't', -Keycode.COMMAND,
                        '']),
        (0x400000, '', [Keycode.COMMAND, 't', -Keycode.COMMAND,
                        '']),
        # Encoder button ---
        (0x000000, '', [Keycode.COMMAND, 'w']) # Close window/tab
    ]
}
