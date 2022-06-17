# SPDX-FileCopyrightText: 2022 Liz Clark for Adafruit Industries
#
# SPDX-License-Identifier: MIT

import sys
import time
import board
from analogio import AnalogIn
from adafruit_pyportal import PyPortal
cwd = ("/"+__file__).rsplit('/', 1)[0] # the current working directory (where this file is)
sys.path.append(cwd)
import openweather_graphics  # pylint: disable=wrong-import-position

# Get wifi details and more from a secrets.py file
try:
    from secrets import secrets
except ImportError:
    print("WiFi secrets are kept in secrets.py, please add them there!")
    raise

# Use cityname, country code where countrycode is ISO3166 format.
# E.g. "New York, US" or "London, GB"
LOCATION = "New York, US"

# Set up where we'll be fetching data from
DATA_SOURCE = "http://api.openweathermap.org/data/2.5/weather?q="+LOCATION
DATA_SOURCE += "&appid="+secrets['openweather_token']
# You'll need to get a token from openweather.org, looks like 'b6907d289e10d714a6e88b30761fae22'
DATA_LOCATION = []


# Initialize the pyportal object and let us know what data to fetch and where
# to display it
pyportal = PyPortal(url=DATA_SOURCE,
                    json_path=DATA_LOCATION,
                    status_neopixel=board.NEOPIXEL,
                    default_bg=0x000000)

display = board.DISPLAY
#  rotate display for portrait orientation
display.rotation = 270

#  instantiate the openweather_graphics class
gfx = openweather_graphics.OpenWeather_Graphics(pyportal.splash, am_pm=True, celsius=False)

#  time keeping for refreshing screen icons and weather information
localtile_refresh = None
weather_refresh = None

#  setup light sensor as an analog input
analogin = AnalogIn(board.LIGHT)

#  analog scaling helper
def getVoltage(pin):
    return (pin.value * 3.3) / 65536

#  timer for updating onscreen clock
clock = time.monotonic()
#  timer for keeping backlight on
light = time.monotonic()
#  light sensor threshold value
threshold = 0.085

while True:
    # only query the online time once per hour (and on first run)
    if (not localtile_refresh) or (time.monotonic() - localtile_refresh) > 3600:
        try:
            print("Getting time from internet!")
            pyportal.get_local_time()
            localtile_refresh = time.monotonic()
        except RuntimeError as e:
            print("Some error occured, retrying! -", e)
            continue
    # only query the weather every 10 minutes (and on first run)
    if (not weather_refresh) or (time.monotonic() - weather_refresh) > 600:
        try:
            value = pyportal.fetch()
            print("Response is", value)
            gfx.display_weather(value)
            weather_refresh = time.monotonic()
        except RuntimeError as e:
            print("Some error occured, retrying! -", e)
            continue
    #  check light sensor
    if getVoltage(analogin) < threshold:
        #  if its blocked then turn on backlight
        pyportal.set_backlight(1)
        #  reset light timer
        light = time.monotonic()
    #  after 10 seconds, turn off the backlight
    if (time.monotonic() - light) > 10:
        pyportal.set_backlight(0)
    #  every 30 seconds update time on screen
    if (time.monotonic() - clock) > 30:
        gfx.update_time()
        clock = time.monotonic()
