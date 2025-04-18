# SPDX-FileCopyrightText: 2019 John Edgar Park for Adafruit Industries
#
# SPDX-License-Identifier: MIT

"""
This project will access the League of Legends API, grab a Summoner's Level
and display it on a screen.
You'll need a Riot API key in your settings.toml file
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

#Choose a valid Summoner name
SUMMONER_NAME = "RiotSchmick"

# Set up where we'll be fetching data from
DATA_SOURCE = "https://na1.api.riotgames.com/lol/summoner/v4/summoners/by-name/"+SUMMONER_NAME
DATA_SOURCE += "?api_key=" + getenv("LEAGUE_TOKEN")
DATA_LOCATION = ["summonerLevel"]
CAPTION = "SUMMONER  "+SUMMONER_NAME

# the current working directory (where this file is)
cwd = ("/"+__file__).rsplit('/', 1)[0]
pyportal = PyPortal(url=DATA_SOURCE,
                    json_path=(DATA_LOCATION),
                    status_neopixel=board.NEOPIXEL,
                    default_bg=cwd+"/lol_background.bmp",
                    text_font=cwd+"/fonts/Collegiate-50.bdf",
                    text_position=(135, 200),
                    text_color=0xffbe33,
                    caption_text=CAPTION,
                    caption_font=cwd+"/fonts/Collegiate-24.bdf",
                    caption_position=(5, 20),
                    caption_color=0xffbe33)

# track the last value so we can play a sound when it updates
last_value = 0

while True:
    try:
        value = pyportal.fetch()
        print("Response is", value)
        if last_value < value:  # ooh it went up!
            print("New level!")
            pyportal.play_file(cwd+"/triode_low_fade.wav")
        last_value = value
    except (ValueError, RuntimeError, ConnectionError, OSError) as e:
        print("Some error occurred, retrying! -", e)
    #check again in two minutes
    time.sleep(60*2)
