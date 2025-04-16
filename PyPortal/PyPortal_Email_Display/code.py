# SPDX-FileCopyrightText: 2019 Brent Rubell for Adafruit Industries
#
# SPDX-License-Identifier: MIT

"""
PyPortal Adafruit IO Feed Display

Displays an Adafruit IO Feed on a PyPortal.
"""

from os import getenv
import time
import board
from adafruit_pyportal import PyPortal

# (visit io.adafruit.com if you need to create an account, or if you need your Adafruit IO key.)
ssid = getenv("CIRCUITPY_WIFI_SSID")
password = getenv("CIRCUITPY_WIFI_PASSWORD")
aio_username = getenv("ADAFRUIT_AIO_USERNAME")
aio_key = getenv("ADAFRUIT_AIO_KEY")

if None in [ssid, password, aio_username, aio_key]:
    raise RuntimeError(
        "WiFi and Adafruit IO settings are kept in settings.toml, "
        "please add them there. The settings file must contain "
        "'CIRCUITPY_WIFI_SSID', 'CIRCUITPY_WIFI_PASSWORD', "
        "'ADAFRUIT_AIO_USERNAME' and 'ADAFRUIT_AIO_KEY' at a minimum."
    )

# Adafruit IO Feed
io_feed = 'zapemail'

DATA_SOURCE = f"https://io.adafruit.com/api/v2/{aio_username}/feeds/{io_feed}?X-AIO-Key={aio_key}"
FEED_VALUE_LOCATION = ['last_value']

cwd = ("/"+__file__).rsplit('/', 1)[0]
pyportal = PyPortal(url=DATA_SOURCE,
                    json_path=FEED_VALUE_LOCATION,
                    status_neopixel=board.NEOPIXEL,
                    default_bg=cwd+"/pyportal_email.bmp",
                    text_font=cwd+"/fonts/Helvetica-Oblique-17.bdf",
                    text_position=(30, 65),
                    text_color=0xFFFFFF,
                    text_wrap=35, # wrap feed after 35 chars
                    text_maxlen=160)

# speed up projects with lots of text by preloading the font!
pyportal.preload_font()

while True:
    try:
        print('Fetching Adafruit IO Feed Value..')
        value = pyportal.fetch()
        print("Response is", value)
    except RuntimeError as e:
        print("Some error occured, retrying! -", e)
    time.sleep(10)
