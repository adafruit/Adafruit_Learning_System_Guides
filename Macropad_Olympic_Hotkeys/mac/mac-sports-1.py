# MACROPAD Olympic Hotkeys sports page 1
# pylint: disable=line-too-long

from adafruit_hid.keycode import Keycode # REQUIRED if using Keycode.* values

app = {                # REQUIRED dict, must be named 'app'
    'name' : 'Sports 1', # Application name
    'macros' : [       # List of button macros...
        # COLOR    LABEL    KEY SEQUENCE
        # 1st row ----------
        # 3x3 basketball schedule and results in new tab
        (0x000040, '3x3Bask', [Keycode.COMMAND, 't', -Keycode.COMMAND,
                               'https://olympics.com/tokyo-2020/olympic-games/en/results/3x3-basketball/olympic-schedule-and-results.htm\n']),
        (0x3F3F3F, 'Arch', [Keycode.COMMAND, 't', -Keycode.COMMAND,
                            'https://olympics.com/tokyo-2020/olympic-games/en/results/archery/olympic-schedule-and-results.htm\n']),
        (0x000040 , 'ArtGym', [Keycode.COMMAND, 't', -Keycode.COMMAND,
                               'https://olympics.com/tokyo-2020/olympic-games/en/results/artistic-gymnastics/olympic-schedule-and-results.htm\n']),
        # 2nd row ----------
        (0x3F3F3F, 'ArtSwim', [Keycode.COMMAND, 't', -Keycode.COMMAND,
                               'https://olympics.com/tokyo-2020/olympic-games/en/results/artistic-swimming/olympic-schedule-and-results.htm\n']),
        (0x404000, 'Athl', [Keycode.COMMAND, 't', -Keycode.COMMAND,
                            'https://olympics.com/tokyo-2020/olympic-games/en/results/athletics/olympic-schedule-and-results.htm\n']),
        (0x3F3F3F , 'Bdmntn', [Keycode.COMMAND, 't', -Keycode.COMMAND,
                               'https://olympics.com/tokyo-2020/olympic-games/en/results/badminton/olympic-schedule-and-results.htm\n']),
        # 3rd row ----------
        (0x404000, 'BB/SB', [Keycode.COMMAND, 't', -Keycode.COMMAND,
                             'https://olympics.com/tokyo-2020/olympic-games/en/results/baseball-softball/olympic-schedule-and-results.htm\n']),
        (0x3F3F3F, 'BaskBl', [Keycode.COMMAND, 't', -Keycode.COMMAND,
                              'https://olympics.com/tokyo-2020/olympic-games/en/results/basketball/olympic-schedule-and-results.htm\n']),
        (0x004000 , 'BVoll', [Keycode.COMMAND, 't', -Keycode.COMMAND,
                              'https://olympics.com/tokyo-2020/olympic-games/en/results/beach-volleyball/olympic-schedule-and-results.htm\n']),
        # 4th row ----------
        (0x3F3F3F, 'Boxing', [Keycode.COMMAND, 't', -Keycode.COMMAND,
                              'https://olympics.com/tokyo-2020/olympic-games/en/results/boxing/olympic-schedule-and-results.htm\n']),
        (0x004000, 'CanoeSl', [Keycode.COMMAND, 't', -Keycode.COMMAND,
                               'https://olympics.com/tokyo-2020/olympic-games/en/results/canoe-slalom/olympic-schedule-and-results.htm\n']),
        (0x3F3F3F, 'CanoeSp', [Keycode.COMMAND, 't', -Keycode.COMMAND,
                               'https://olympics.com/tokyo-2020/olympic-games/en/results/canoe-sprint/olympic-schedule-and-results.htm \n']),
        # Encoder button ---
        (0x000000, '', [Keycode.COMMAND, 'w']) # Close window/tab
    ]
}
