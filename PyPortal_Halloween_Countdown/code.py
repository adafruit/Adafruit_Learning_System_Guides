"""
PyPortal based countdown of days until Halloween.

Adafruit invests time and resources providing this open source code.
Please support Adafruit and open source hardware by purchasing
products from Adafruit!

Written by Dave Astels for Adafruit Industries
Copyright (c) 2019 Adafruit Industries
Licensed under the MIT license.

All text above must be included in any redistribution.
"""

#pylint:disable=invalid-name
import time
import random
import board
from adafruit_pyportal import PyPortal
from adafruit_bitmap_font import bitmap_font
from adafruit_display_text.label import Label

try:
    from secrets import secrets
except ImportError:
    print("""WiFi settings are kept in secrets.py, please add them there!
the secrets dictionary must contain 'ssid' and 'password' at a minimum""")
    raise

# The time of the thing!
EVENT_YEAR = 2019
EVENT_MONTH = 10
EVENT_DAY = 31
# we'll make a python-friendly structure
event_time = time.struct_time((EVENT_YEAR, EVENT_MONTH, EVENT_DAY,
                               0, 0, 0,  # we don't track hours, minutes, or seconds
                               -1, -1, False))  # we dont know day of week/year or DST

# determine the current working directory
# needed so we know where to find files
cwd = ("/"+__file__).rsplit('/', 1)[0]

big_font = bitmap_font.load_font(cwd+"/fonts/Terror-94.bdf")
big_font.load_glyphs(b'0123456789') # pre-load glyphs for fast printing

backgrounds = ['background_1.bmp',
               'background_2.bmp',
               'background_3.bmp',
               'background_4.bmp',
               'background_5.bmp',
               'background_6.bmp',
               'background_7.bmp',
               'background_8.bmp',
               'background_9.bmp',
               'background_10.bmp',
               'background_11.bmp',
               'background_12.bmp',
               'background_13.bmp',
               'background_14.bmp',
               'background_15.bmp',
               'background_16.bmp',
               'background_17.bmp']

event_background = cwd+"/happy_halloween.bmp"

# Initialize the pyportal object and let us know what data to fetch and where
# to display it
pyportal = PyPortal(status_neopixel=board.NEOPIXEL,
                    default_bg=cwd + backgrounds[0],
                    caption_text='DAYS  REMAINING',
                    caption_font=cwd+'/fonts/Terror-31.bdf',
                    caption_position=(24, 218),
                    caption_color=0x000000)

countdown_text = Label(big_font, max_glyphs=3)
countdown_text.x = 25
countdown_text.y = 120
countdown_text.color = 0x7942a0
pyportal.splash.append(countdown_text)

refresh_time = None

while True:
    # only query the online time once per hour (and on first run)
    if (not refresh_time) or (time.monotonic() - refresh_time) > 3600:
        try:
            print("Getting time from internet!")
            pyportal.get_local_time(location=secrets['timezone'])
            refresh_time = time.monotonic()
        except RuntimeError as e:
            print("Some error occured, retrying! -", e)
            continue

    timestamp = time.localtime()
    now = time.struct_time((timestamp[0], timestamp[1], timestamp[2],
                            0, 0, 0,  # we don't track seconds
                            -1, -1, False))  # we dont know day of week/year or DST

    print("Current time:", now)
    remaining = time.mktime(event_time) - time.mktime(now)
    print("Time remaining (s):", remaining)
    if remaining == 0:
        # oh, its event time!
        pyportal.set_background(event_background)
        countdown_text.text = ''
        pyportal.set_caption('', (13, 215), 0x000000)
        while True:  # that's all folks
            pass
    days_remaining = remaining // 86400
    print("%d days remaining" % (days_remaining))
    countdown_text.text = '{:>3}'.format(days_remaining)
    pyportal.set_background(backgrounds[random.randint(0, len(backgrounds) - 1)])

    # update every minute
    time.sleep(60)
