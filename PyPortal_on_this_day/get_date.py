"""
Get the current day and return string as 'xx/xx'
"""

import time
import board
import neopixel
from adafruit_pyportal import PyPortal
from adafruit_bitmap_font import bitmap_font
from adafruit_display_text.Label import Label

# determine the current working directory
# needed so we know where to find files
cwd = ("/"+__file__).rsplit('/', 1)[0]

# initialize the pyportal object and let us know what data to fetch and where
# to display it
pyportal = PyPortal(status_neopixel=board.NEOPIXEL,
                    default_bg=0x000000)



while True:
    try:
        print("Getting time from internet!")
        pyportal.get_local_time()
    except RuntimeError as e:
        print("Some error occured, retrying! -", e)
        continue
    break


refresh_time = None

while True:
    time_now = time.localtime()
    # only query the online time once per hour (and on first run)
    if (not refresh_time) or (time.monotonic() - refresh_time) > 3600:
        try:
            print("Getting time from internet!")
            pyportal.get_local_time()
            refresh_time = time.monotonic()
            month, day = time_now[1:3]
            #month = time_now[1]
            #day = time_now[2]
            print("the day is")
            print(month, "_", day)

        except RuntimeError as e:
            print("Some error occured, retrying! -", e)
            continue

