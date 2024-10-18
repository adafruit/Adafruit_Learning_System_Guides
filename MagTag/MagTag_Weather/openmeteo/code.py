# SPDX-FileCopyrightText: 2024 Carter Nelson for Adafruit Industries
#
# SPDX-License-Identifier: MIT
# pylint: disable=redefined-outer-name, eval-used, wrong-import-order, unsubscriptable-object

import time
import terminalio
import displayio
import adafruit_imageload
from adafruit_display_text import label
from adafruit_magtag.magtag import MagTag

# --| USER CONFIG |--------------------------
LAT = 47.6                  # latitude
LON = -122.3                # longitude
TMZ = "America/Los_Angeles" # https://en.wikipedia.org/wiki/List_of_tz_database_time_zones
METRIC = False              # set to True for metric units
CITY = None                 # optional
# -------------------------------------------

# ----------------------------
# Define various assets
# ----------------------------
BACKGROUND_BMP = "/bmps/weather_bg.bmp"
ICONS_LARGE_FILE = "/bmps/weather_icons_70px.bmp"
ICONS_SMALL_FILE = "/bmps/weather_icons_20px.bmp"
DAYS = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday")
MONTHS = (
    "January",
    "February",
    "March",
    "April",
    "May",
    "June",
    "July",
    "August",
    "September",
    "October",
    "November",
    "December",
)

# Weather Code Information from https://open-meteo.com/en/docs
# Code 	Description
# 0 	Clear sky
# 1, 2, 3 	Mainly clear, partly cloudy, and overcast
# 45, 48 	Fog and depositing rime fog
# 51, 53, 55 	Drizzle: Light, moderate, and dense intensity
# 56, 57 	Freezing Drizzle: Light and dense intensity
# 61, 63, 65 	Rain: Slight, moderate and heavy intensity
# 66, 67 	Freezing Rain: Light and heavy intensity
# 71, 73, 75 	Snow fall: Slight, moderate, and heavy intensity
# 77 	Snow grains
# 80, 81, 82 	Rain showers: Slight, moderate, and violent
# 85, 86 	Snow showers slight and heavy
# 95 * 	Thunderstorm: Slight or moderate
# 96, 99 * 	Thunderstorm with slight and heavy hail

# Map the above WMO codes to index of icon in 3x3 spritesheet
WMO_CODE_TO_ICON = (
    (0,),                                       # 0 = sunny
    (1,),                                       # 1 = partly sunny/cloudy
    (2,),                                       # 2 = cloudy
    (3,),                                       # 3 = very cloudy
    (61, 63, 65),                               # 4 = rain
    (51, 53, 55, 80, 81, 82),                   # 5 = showers
    (95, 96, 99),                               # 6 = storms
    (56, 57, 66, 67, 71, 73, 75, 77, 85, 86),   # 7 = snow
    (45, 48),                                   # 8 = fog and stuff
)

magtag = MagTag()

# ----------------------------
# Backgrounnd bitmap
# ----------------------------
magtag.graphics.set_background(BACKGROUND_BMP)

# ----------------------------
# Weather icons sprite sheet
# ----------------------------
icons_large_bmp, icons_large_pal = adafruit_imageload.load(ICONS_LARGE_FILE)
icons_small_bmp, icons_small_pal = adafruit_imageload.load(ICONS_SMALL_FILE)

# /////////////////////////////////////////////////////////////////////////
#  helper functions

def get_forecast():
    URL  = f"https://api.open-meteo.com/v1/forecast?latitude={LAT}&longitude={LON}&"
    URL += "daily=weather_code,temperature_2m_max,temperature_2m_min"
    URL += ",sunrise,sunset,wind_speed_10m_max,wind_direction_10m_dominant"
    URL += "&timeformat=unixtime"
    URL += f"&timezone={TMZ}"
    resp = magtag.network.fetch(URL)
    return resp


def make_banner(x=0, y=0):
    """Make a single future forecast info banner group."""
    day_of_week = label.Label(terminalio.FONT, text="DAY", color=0x000000)
    day_of_week.anchor_point = (0, 0.5)
    day_of_week.anchored_position = (0, 10)

    icon = displayio.TileGrid(
        icons_small_bmp,
        pixel_shader=icons_small_pal,
        x=25,
        y=0,
        width=1,
        height=1,
        tile_width=20,
        tile_height=20,
    )

    day_temp = label.Label(terminalio.FONT, text="+100F", color=0x000000)
    day_temp.anchor_point = (0, 0.5)
    day_temp.anchored_position = (50, 10)

    group = displayio.Group(x=x, y=y)
    group.append(day_of_week)
    group.append(icon)
    group.append(day_temp)

    return group


def temperature_text(tempC):
    if METRIC:
        return "{:3.0f}C".format(tempC)
    else:
        return "{:3.0f}F".format(32.0 + 1.8 * tempC)


def wind_text(speedkmh, direction):
    wind_dir = "N"
    if direction < 337:
        wind_dir = "NW"
    if direction < 293:
        wind_dir = "W"
    if direction < 247:
        wind_dir = "SW"
    if direction < 202:
        wind_dir = "S"
    if direction < 157:
        wind_dir = "SE"
    if direction < 112:
        wind_dir = "E"
    if direction < 67:
        wind_dir = "NE"
    if direction < 22:
        wind_dir = "N"

    wtext = f"from {wind_dir} "

    if METRIC:
        wtext += "{:2.0f}kmh".format(speedkmh)
    else:
        wtext += "{:2.0f}mph".format(0.621371 * speedkmh)
    return wtext


def update_today(data):
    """Update today weather info."""
    # date text
    s = data["daily"]["time"][0] + data["utc_offset_seconds"]
    t = time.localtime(s)
    today_date.text = "{} {} {}, {}".format(
        DAYS[t.tm_wday].upper(),
        MONTHS[t.tm_mon - 1].upper(),
        t.tm_mday,
        t.tm_year
    )
    # weather icon
    w = data["daily"]["weather_code"][0]
    today_icon[0] = next(i for i, t in enumerate(WMO_CODE_TO_ICON) if w in t)
    # temperatures
    today_low_temp.text = temperature_text(data["daily"]["temperature_2m_min"][0])
    today_high_temp.text = temperature_text(data["daily"]["temperature_2m_max"][0])
    # wind
    s = data["daily"]["wind_speed_10m_max"][0]
    d = data["daily"]["wind_direction_10m_dominant"][0]
    today_wind.text = wind_text(s, d)
    # sunrise/set
    sr = time.localtime(data["daily"]["sunrise"][0] + data["utc_offset_seconds"])
    ss = time.localtime(data["daily"]["sunset"][0] + data["utc_offset_seconds"])
    today_sunrise.text = "{:2d}:{:02d} AM".format(sr.tm_hour, sr.tm_min)
    today_sunset.text = "{:2d}:{:02d} PM".format(ss.tm_hour - 12, ss.tm_min)


def update_future(data):
    """Update the future forecast info."""
    for i, banner in enumerate(future_banners):
        # day of week
        s = data["daily"]["time"][i+1] + data["utc_offset_seconds"]
        t = time.localtime(s)
        banner[0].text = DAYS[t.tm_wday][:3].upper()
        # weather icon
        w = data["daily"]["weather_code"][i+1]
        banner[1][0] = next(x for x, t in enumerate(WMO_CODE_TO_ICON) if w in t)
        # temperature
        t = data["daily"]["temperature_2m_max"][i+1]
        banner[2].text = temperature_text(t)


def go_to_sleep(current_time_secs):
    """Enter deep sleep for time needed."""
    # work in units of seconds
    seconds_in_a_day = 24 * 60 * 60
    three_fifteen = (3 * 60 + 15) * 60
    # wake up 15 minutes after 3am
    seconds_to_sleep = (seconds_in_a_day - current_time_secs) + three_fifteen
    print(
        "Sleeping for {} hours, {} minutes".format(
            seconds_to_sleep // 3600, (seconds_to_sleep // 60) % 60
        )
    )
    magtag.exit_and_deep_sleep(seconds_to_sleep)


# ===========
# U I
# ===========
today_date = label.Label(terminalio.FONT, text="?" * 30, color=0x000000)
today_date.anchor_point = (0, 0)
today_date.anchored_position = (15, 14)

location_name = label.Label(terminalio.FONT, color=0x000000)
if CITY:
    location_name.text = f"{CITY[:16]} ({LAT:.1f},{LON:.1f})"
else:
    location_name.text = f"({LAT},{LON})"

location_name.anchor_point = (0, 0)
location_name.anchored_position = (15, 25)

today_icon = displayio.TileGrid(
    icons_large_bmp,
    pixel_shader=icons_small_pal,
    x=10,
    y=40,
    width=1,
    height=1,
    tile_width=70,
    tile_height=70,
)

today_low_temp = label.Label(terminalio.FONT, text="+100F", color=0x000000)
today_low_temp.anchor_point = (0.5, 0)
today_low_temp.anchored_position = (122, 60)

today_high_temp = label.Label(terminalio.FONT, text="+100F", color=0x000000)
today_high_temp.anchor_point = (0.5, 0)
today_high_temp.anchored_position = (162, 60)

today_wind = label.Label(terminalio.FONT, text="99m/s", color=0x000000)
today_wind.anchor_point = (0, 0.5)
today_wind.anchored_position = (110, 95)

today_sunrise = label.Label(terminalio.FONT, text="12:12 PM", color=0x000000)
today_sunrise.anchor_point = (0, 0.5)
today_sunrise.anchored_position = (45, 117)

today_sunset = label.Label(terminalio.FONT, text="12:12 PM", color=0x000000)
today_sunset.anchor_point = (0, 0.5)
today_sunset.anchored_position = (130, 117)

today_banner = displayio.Group()
today_banner.append(today_date)
today_banner.append(location_name)
today_banner.append(today_icon)
today_banner.append(today_low_temp)
today_banner.append(today_high_temp)
today_banner.append(today_wind)
today_banner.append(today_sunrise)
today_banner.append(today_sunset)

future_banners = [
    make_banner(x=210, y=18),
    make_banner(x=210, y=39),
    make_banner(x=210, y=60),
    make_banner(x=210, y=81),
    make_banner(x=210, y=102),
]

magtag.splash.append(today_banner)
for future_banner in future_banners:
    magtag.splash.append(future_banner)

# ===========
#  M A I N
# ===========
print("Fetching forecast...")
resp_data = get_forecast()
forecast_data = resp_data.json()

print("Updating...")
update_today(forecast_data)
update_future(forecast_data)

print("Refreshing...")
time.sleep(magtag.display.time_to_refresh + 1)
magtag.display.refresh()
time.sleep(magtag.display.time_to_refresh + 1)

print("Sleeping...")
h, m, s = (int(t) for t in resp_data.headers['date'].split(" ")[4].split(':'))
current_time_secs = (h * 3600) + (m * 60) + (s) + forecast_data['utc_offset_seconds']
go_to_sleep(current_time_secs)
#  entire code will run again after deep sleep cycle
#  similar to hitting the reset button

