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
import time
import adafruit_binascii as binascii
import json
import board
from adafruit_pyportal import PyPortal
import adafruit_requests as requests

try:
    from secrets import secrets
except ImportError:
    print("""WiFi settings are kept in secrets.py, please add them there!
the secrets dictionary must contain 'ssid' and 'password' at a minimum""")
    raise

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
bearer_token = secrets['twitter_bearer_token']
pyportal.set_headers({'Authorization': 'Bearer ' + bearer_token})

while True:
    pyportal.fetch()
    time.sleep(3600)       # check every hour