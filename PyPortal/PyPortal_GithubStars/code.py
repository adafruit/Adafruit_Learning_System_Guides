# SPDX-FileCopyrightText: 2019 Limor Fried for Adafruit Industries
#
# SPDX-License-Identifier: MIT

"""
This example will access the github API, grab a number like
the number of stars for a repository... and display it on a screen!
if you can find something that spits out JSON data, we can display it
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
DATA_SOURCE = "https://api.github.com/repos/adafruit/circuitpython"
CAPTION = "www.github.com/adafruit/circuitpython"
# If we have an access token, we can query more often
github_token = getenv("github_token")
if github_token:
    DATA_SOURCE += f"?access_token={github_token}"

# The data we want to display
DATA_LOCATION = ["stargazers_count"]

cwd = ("/"+__file__).rsplit('/', 1)[0]
pyportal = PyPortal(url=DATA_SOURCE, json_path=DATA_LOCATION,
                    status_neopixel=board.NEOPIXEL,
                    default_bg=cwd+"/stars_background.bmp",
                    text_font=cwd+"/fonts/Collegiate-50.bdf",
                    text_position=(200, 100),
                    text_color=0xFFFFFF,
                    caption_text=CAPTION,
                    caption_font=cwd+"/fonts/Arial.bdf",
                    caption_position=(40, 220),
                    caption_color=0xFFFFFF)

# track the last value so we can play a sound when it updates
last_value = 0

while True:
    try:
        value = pyportal.fetch()
        print("Response is", value)
        if last_value < value:  # ooh it went up!
            print("New star!")
            pyportal.play_file(cwd+"/coin.wav")
        last_value = value
    except (ValueError, RuntimeError, ConnectionError, OSError) as e:
        print("Some error occured, retrying! -", e)

    time.sleep(60)  # wait a minute before getting again
