# SPDX-FileCopyrightText: 2022 Liz Clark for Adafruit Industries
#
# SPDX-License-Identifier: MIT

from os import getenv
import sys
import time
import board
from analogio import AnalogIn
from adafruit_pyportal import PyPortal
cwd = ("/"+__file__).rsplit('/', 1)[0] # the current working directory (where this file is)
sys.path.append(cwd)
import openweather_graphics  # pylint: disable=wrong-import-position

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

# Use cityname, country code where countrycode is ISO3166 format.
# E.g. "New York, US" or "London, GB"
LOCATION = "New York, US"

# Set up where we'll be fetching data from
DATA_SOURCE = "http://api.openweathermap.org/data/2.5/weather?q="+LOCATION
DATA_SOURCE += "&appid=" + getenv('openweather_token')
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
light_clock = time.monotonic()
#  timer for checking the light sensor
switch_clock = time.monotonic()
#  variable to scale light sensor reading
ratio = 0
#  storing last light sensor ratio reading
last_ratio = 0

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
    #  every 0.1 seconds check the light sensor value
    if (time.monotonic() - switch_clock) > 0.1:
        #  read the light sensor and scale it 0 to 3.3
        reading = getVoltage(analogin)
        #  calculate the % of light out of the maximum light
        ratio = ((ratio + pow(1.0 - reading / 3.3, 4.0)) / 2.0)
        #  create a comparison ratio with the last reading
        power_ratio = last_ratio + pow(last_ratio, 2.0)
        #  if the comparison ratio is less than 1
        if power_ratio < 1:
            #  and the current ratio is larger
            if ratio > power_ratio:
                #  turn on the backlight
                pyportal.set_backlight(1)
                light_clock = time.monotonic()
        #  otherwise (if in a darker room)
        else:
            #  if there's a difference greater than 0.003
            #  between the current ratio and the last ratio
            if ratio - last_ratio > 0.003:
                #  turn on the backlight
                pyportal.set_backlight(1)
                light_clock = time.monotonic()
        #  update last_ratio
        last_ratio = ratio
        switch_clock = time.monotonic()
    #  after 10 seconds, turn off the backlight
    if (time.monotonic() - light_clock) > 10:
        pyportal.set_backlight(0)
    #  every 30 seconds update time on screen
    if (time.monotonic() - clock) > 30:
        gfx.update_time()
        clock = time.monotonic()
