# SPDX-FileCopyrightText: 2019 Limor Fried for Adafruit Industries
#
# SPDX-License-Identifier: MIT

"""
This example will access the adafruit.io API, grab a number like active users
and io plus subscribers... and display it on a screen
If you can find something that spits out JSON data, we can display it!
"""

from os import getenv
import time
import board
from adafruit_pyportal import PyPortal

# Get WiFi details and Adafruit IO keys, ensure these are setup in settings.toml
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

# Set up where we'll be fetching data from
DATA_SOURCE = f"https://io.adafruit.com/api/v2/stats?x-aio-key={aio_key}"
DATA_LOCATION1 = ["io_plus", "io_plus_subscriptions"]
DATA_LOCATION2 = ["users", "users_active_30_days"]

cwd = ("/"+__file__).rsplit('/', 1)[0]
print(cwd)
pyportal = PyPortal(url=DATA_SOURCE,
                    json_path=(DATA_LOCATION1, DATA_LOCATION2),
                    status_neopixel=board.NEOPIXEL,
                    default_bg=cwd+"/adafruitio_background.bmp",
                    text_font=cwd+"/fonts/Collegiate-24.bdf",
                    text_position=((165, 170), (165, 200)),
                    text_color=(0x00FF00, 0x0000FF))

while True:
    try:
        value = pyportal.fetch()
        print("Response is", value)
    except RuntimeError as e:
        print("Some error occured, retrying! -", e)

    time.sleep(60)
