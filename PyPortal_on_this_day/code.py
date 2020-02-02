"""
'of this day' demo
Display notable info about famous electronics-related peoples
Data sources: https://github.com/adafruit/OTD/tree/master/electronics
"""

import time
import board
from adafruit_pyportal import PyPortal

cwd = ("/"+__file__).rsplit('/', 1)[0] # the current working directory (where this file is)

DAY = ["Day of the year"]
PERSON = ["Person"]
NOTABLE = ["Notable for"]
YEAR = ["Year"]
ACCOMPLISH = ["Accomplishment"]
WEB = ["Web Reference"]

BASE_DATA = "https://raw.githubusercontent.com/adafruit/OTD/master/electronics/"

# a function that returns whatever is passed in
def identity(x):
    return x

# create pyportal object w no data source (we'll feed it text later)
pyportal = PyPortal(url = BASE_DATA, debug=True,
                    json_path = (DAY, PERSON, NOTABLE, YEAR, ACCOMPLISH, WEB),
                    status_neopixel = board.NEOPIXEL,
                    default_bg = cwd + "/on_this_day_bg.bmp",
                    text_font = cwd+"fonts/Arial-ItalicMT-17.bdf",
                    text_transform = [identity]*6,  # we do this so the date doesnt get commas
                    text_position=((10, 70), (10, 100), (10, 130),(60, 160), (105, 190), (10, 220)),
                    text_color=(0xFFFFFF, 0xFFFFFF, 0xFFFFFF, 0xFFFFFF, 0xFFFFFF, 0xFFFFFF),
                    text_maxlen=(50, 50, 50, 50, 50, 50), # cut off characters
                   )

while True:
    try:
        print("Getting time from internet!")
        pyportal.get_local_time()
        refresh_time = time.monotonic()
    except RuntimeError as e:
        print("Some error occured, retrying! -", e)
        continue

    now = time.localtime()
    print("Current time:", now)
    url = BASE_DATA+"%02d_%02d.json" % (now.tm_mon, now.tm_mday)
    print(url)
    response = None
    try:
        response = pyportal.fetch(url)
        print("Response is", response)
    except RuntimeError as e:
        print("Some error occured, retrying! -", e)

    # Make a QR code from web reference
    pyportal.show_QR(bytearray(response[5]), qr_size=3,
                     x=220, y=10)

    # wait 10 minutes before running again
    time.sleep(10*60)
