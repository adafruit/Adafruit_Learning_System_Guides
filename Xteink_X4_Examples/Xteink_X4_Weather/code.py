# SPDX-FileCopyrightText: 2026 Liz Clark for Adafruit Industries
#
# SPDX-License-Identifier: MIT
# pylint: disable=redefined-outer-name, eval-used, wrong-import-order, unsubscriptable-object

"""
Xteink X4 Weather Display Demo
Based on MagTag Weather by Carter Nelson
"""

import time
import os
import board
import alarm
import displayio
import adafruit_imageload
import ssl
import wifi
import socketpool
import adafruit_requests
from adafruit_bitmap_font import bitmap_font
from adafruit_display_text import label
import gc

gc.collect()

display = board.DISPLAY
display.rotation = 270
DISPLAY_WIDTH = display.width

try:
    wifi.radio.connect(os.getenv('CIRCUITPY_WIFI_SSID'), os.getenv('CIRCUITPY_WIFI_PASSWORD'))
except TypeError:
    print("Could not find WiFi info. Check your settings.toml file!")
    raise

# --| USER CONFIG |--------------------------
LAT = 40.7128  # latitude
LON = -74.0060  # longitude
TMZ = "America/New_York"  # https://en.wikipedia.org/wiki/List_of_tz_database_time_zones
METRIC = False  # set to True for metric units
CITY = "New York, NY"  # optional
# -------------------------------------------

pool = socketpool.SocketPool(wifi.radio)
requests = adafruit_requests.Session(pool, ssl.create_default_context())
URL = f"https://api.open-meteo.com/v1/forecast?latitude={LAT}&longitude={LON}&"
URL += "daily=weather_code,temperature_2m_max,temperature_2m_min"
URL += ",sunrise,sunset"
URL += "&timeformat=unixtime"
URL += f"&timezone={TMZ}"
gc.collect()
resp_data = requests.get(URL)
#resp_data = get_forecast()
print("got url")
forecast_data = resp_data.json()

# ----------------------------
# Define various assets
# ----------------------------
gc.collect()
font_file = "/fonts/Arial-Bold-24.bdf"
font = bitmap_font.load_font(font_file)
BACKGROUND_BMP = "/bmps/weather_bg_vert.bmp"
ICONS_LARGE_FILE = "/bmps/weather-icons.bmp"
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
    (0,),  # 0 = sunny
    (1,),  # 1 = partly sunny/cloudy
    (2, 3, 45, 48,),  # 2 = cloudy/very cloudy/fog
    (61, 63, 65, 51, 53, 55, 80, 81, 82),  # 4 = rain/showers
    (95, 96, 99),  # 6 = storms
    (56, 57, 66, 67, 71, 73, 75, 77, 85, 86),  # 7 = snow
)

# ----------------------------
# Backgrounnd bitmap
# ----------------------------
gc.collect()
splash = displayio.Group()
bitmap = displayio.OnDiskBitmap(BACKGROUND_BMP)
tile_grid = displayio.TileGrid(bitmap, pixel_shader=bitmap.pixel_shader)
splash.append(tile_grid)
display.root_group = splash
print("got background")

# ----------------------------
# Weather icons sprite sheet
# ----------------------------
gc.collect()
icons_large_bmp, icons_large_pal = adafruit_imageload.load(ICONS_LARGE_FILE)
print("got icon sheet")

# /////////////////////////////////////////////////////////////////////////
#  helper functions

def temperature_text(tempC):
    if METRIC:
        return "{:3.0f}C".format(tempC)
    else:
        return "{:3.0f}F".format(32.0 + 1.8 * tempC)


def update_today(data):
    """Update today weather info."""
    # date text
    s = data["daily"]["time"][0] + data["utc_offset_seconds"]
    t = time.localtime(s)
    today_day.text = "{}".format(
        DAYS[t.tm_wday].upper())
    print(today_day.text)
    today_date.text = "{} {}, {}".format(
        MONTHS[t.tm_mon - 1].upper(), t.tm_mday, t.tm_year
    )
    # weather icon
    w = data["daily"]["weather_code"][0]
    today_icon[0] = next(i for i, t in enumerate(WMO_CODE_TO_ICON) if w in t)
    # temperatures
    today_temp.text = f"H: {temperature_text(data['daily']['temperature_2m_max'][0])} "
    today_temp.text += f"L: {temperature_text(data['daily']['temperature_2m_min'][0])}"
    # sunrise/set
    sr = time.localtime(data["daily"]["sunrise"][0] + data["utc_offset_seconds"])
    ss = time.localtime(data["daily"]["sunset"][0] + data["utc_offset_seconds"])
    today_sunrise.text = "{:2d}:{:02d} AM".format(sr.tm_hour, sr.tm_min)
    today_sunset.text = "{:2d}:{:02d} PM".format(ss.tm_hour - 12, ss.tm_min)

# ===========
# U I
# ===========
print("making ui")
today_day = label.Label(font, text="?" * 30, color=0x000000)
today_day.anchor_point = (0.5, 0)
today_day.anchored_position = (DISPLAY_WIDTH / 2, 106)
today_date = label.Label(font, text="?" * 30, color=0x000000)
today_date.anchor_point = (0.5, 0)
today_date.anchored_position = (DISPLAY_WIDTH / 2, 140)

location_name = label.Label(font, color=0x000000)
if CITY:
    location_name.text = f"{CITY[:16]}"
else:
    location_name.text = f"({LAT},{LON})"
location_name.anchor_point = (0.5, 0)
location_name.anchored_position = (DISPLAY_WIDTH / 2, 210)

today_icon = displayio.TileGrid(
    icons_large_bmp,
    pixel_shader=icons_large_pal,
    x=203,
    y=275,
    width=1,
    height=1,
    tile_width=74,
    tile_height=74,
)
today_icon.x = int(DISPLAY_WIDTH / 2 - today_icon.tile_width / 2)

today_temp = label.Label(font, text="H: +100F", color=0x000000)
today_temp.anchor_point = (0, 0)
today_temp.anchored_position = (163, 415)

today_sunrise = label.Label(font, text="12:12 PM", color=0x000000)
today_sunrise.anchor_point = (0, 0)
today_sunrise.anchored_position = (202, 520)

today_sunset = label.Label(font, text="12:12 PM", color=0x000000)
today_sunset.anchor_point = (0, 0)
today_sunset.anchored_position = (202, 614)
today_banner = displayio.Group()
today_banner.append(today_day)
today_banner.append(today_date)
today_banner.append(location_name)
today_banner.append(today_icon)
today_banner.append(today_temp)
today_banner.append(today_sunrise)
today_banner.append(today_sunset)

display.root_group.append(today_banner)

# ===========
#  M A I N
# ===========
gc.collect()
print("Updating...")
update_today(forecast_data)

print("Refreshing...")
time.sleep(display.time_to_refresh + 1)
display.refresh()
time.sleep(display.time_to_refresh + 1)

print("Sleeping...")
wake_alarm = alarm.wake_alarm
pin_alarm = alarm.pin.PinAlarm(pin=board.BUTTON, value=False, pull=True)
alarm.exit_and_deep_sleep_until_alarms(pin_alarm)
#  entire code will run again
