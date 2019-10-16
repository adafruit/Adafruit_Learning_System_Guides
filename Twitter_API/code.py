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
import binascii
import json
import board
from adafruit_pyportal import PyPortal
import adafruit_esp32spi.adafruit_esp32spi_requests as requests

username = 'codewisdom'

try:
    from secrets import secrets
except ImportError:
    print("""WiFi settings are kept in secrets.py, please add them there!
the secrets dictionary must contain 'ssid' and 'password' at a minimum""")
    raise

def halt_and_catch_fire(message, *args):
    """Log a critical error and stall the system."""
    print(message % args)
    while True:
        pass

def get_bearer_token():
    """Get the bearer authentication token from twitter."""
    raw_key = secrets['twitter_api_key'] + ':' + secrets['twitter_secret_key']
    encoded_key = binascii.b2a_base64(bytes(raw_key, 'utf8'))
    string_key = bytes.decode(encoded_key)
    headers = {'Authorization': 'Basic ' + string_key,
               'Content-Type': 'application/x-www-form-urlencoded;charset=UTF-8'}
    response = requests.post('https://api.twitter.com/oauth2/token',
                             headers=headers,
                             data='grant_type=client_credentials')
    response_dict = json.loads(response.content)
    if response_dict['token_type'] != 'bearer':
        halt_and_catch_fire('Wrong token type from twitter: %s', response_dict['token_type'])
    return response_dict['access_token']

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

bearer_token = get_bearer_token()

pyportal.set_headers({'Authorization': 'Bearer ' + bearer_token})

while True:
    pyportal.fetch()
    time.sleep(3600)       # check every hour
