# SPDX-FileCopyrightText: 2019 Dave Astels for Adafruit Industries
#
# SPDX-License-Identifier: MIT

"""
Twitter API for PyPortal.

Adafruit invests time and resources providing this open source code.
Please support Adafruit and open source hardware by purchasing
products from Adafruit!

Written by Dave Astels for Adafruit Industries
Copyright (c) 2019 Adafruit Industries
Licensed under the MIT license.

All text above must be included in any redistribution.
"""

#pylint:disable=invalid-name

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

# Set this to the username you'd like to display tweets from
username = 'codewisdom'

# determine the current working directory
# needed so we know where to find files
cwd = ("/"+__file__).rsplit('/', 1)[0]
url = 'https://api.twitter.com/1.1/statuses/user_timeline.json?count=1&screen_name=' + username


# Initialize the pyportal object and let us know what data to fetch and where
# to display it
pyportal = PyPortal(url=url,
                    json_path=(0, 'text'),
                    status_neopixel=board.NEOPIXEL,
                    default_bg=cwd + '/twitter_background.bmp',
                    text_font=cwd+'/fonts/Helvetica-Bold-16.bdf',
                    text_position=(20, 60),
                    text_color=0xFFFFFF,
                    text_wrap=35,
                    caption_text='@' + username,
                    caption_font=cwd+'/fonts/Helvetica-Bold-16.bdf',
                    caption_position=(5, 210),
                    caption_color=0x808080)

# Set OAuth2.0 Bearer Token
bearer_token = getenv('twitter_bearer_token')
pyportal.set_headers({'Authorization': 'Bearer ' + bearer_token})

while True:
    pyportal.fetch()
    time.sleep(3600)       # check every hour
