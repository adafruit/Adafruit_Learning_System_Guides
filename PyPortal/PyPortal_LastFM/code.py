# SPDX-FileCopyrightText: 2019 Limor Fried for Adafruit Industries
#
# SPDX-License-Identifier: MIT

"""
This example will access the lastFM API, grab a number like subreddit followers
and display it on a screen
If you can find something that spits out JSON data, we can display it!
"""

from os import getenv
import time
import board
from adafruit_pyportal import PyPortal

# Get WiFi details, ensure these are setup in settings.toml
ssid = getenv("CIRCUITPY_WIFI_SSID")
password = getenv("CIRCUITPY_WIFI_PASSWORD")

if None in [ssid, password]:
    raise RuntimeError(
        "WiFi settings are kept in settings.toml, "
        "please add them there. The settings file must contain "
        "'CIRCUITPY_WIFI_SSID', 'CIRCUITPY_WIFI_PASSWORD', "
        "at a minimum."
    )

# Set up where we'll be fetching data from
DATA_SOURCE = "http://ws.audioscrobbler.com/2.0/?method=user.getrecenttracks&limit=1&format=json"
CAPTION = "www.last.fm/user"
# If we have an access token, we can query more often
lfm_username = getenv("lfm_username")
lfm_key = getenv("lfm_key")
if lfm_username:
    DATA_SOURCE += "&user=" + lfm_username
    CAPTION += "/" + lfm_username
if lfm_key:
    DATA_SOURCE += "&api_key=" + lfm_key
print(DATA_SOURCE)

# Total number of plays
DATA_LOCATION = ["recenttracks", "@attr", "totalPages"]

# the current working directory (where this file is)
cwd = ("/"+__file__).rsplit('/', 1)[0]
pyportal = PyPortal(url=DATA_SOURCE, json_path=DATA_LOCATION,
                    status_neopixel=board.NEOPIXEL,
                    default_bg=cwd+"/lastfm_background.bmp",
                    text_font=cwd+"/fonts/Collegiate-50.bdf",
                    text_position=(150, 160),
                    text_color=0xFFFFFF,
                    caption_text=CAPTION,
                    caption_font=cwd+"/fonts/Collegiate-24.bdf",
                    caption_position=(40, 220),
                    caption_color=0xFFFFFF,
                    debug=True)

# track the last value so we can play a sound when it updates
last_value = 0

while True:
    try:
        value = pyportal.fetch()
        print("Response is", value)
    except RuntimeError as e:
        print("Some error occured, retrying! -", e)

    time.sleep(60)
