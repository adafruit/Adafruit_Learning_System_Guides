# SPDX-FileCopyrightText: 2025 Tim C, written for Adafruit Industries
#
# SPDX-License-Identifier: MIT
"""
50 Cent Consumer Price Index Tracker

This project illustrates how to fetch CPI data from the
US Bureau of Labor Statistics API. CPI data from 1994,
when 50 Cent adopted his moniker, is compared with the latest
data to determine how much 50 Cent from 1994 is worth today.
"""
import json
import os
import time

import alarm
import displayio
from displayio import OnDiskBitmap, TileGrid, Group
import supervisor
from terminalio import FONT
import wifi

import adafruit_connection_manager
from adafruit_display_text.text_box import TextBox
import adafruit_requests


# CPI Data URL
latest_cpi_url = "https://api.bls.gov/publicAPI/v2/timeseries/data/CUUR0000SA0"
# CUUR0000SA0 the series ID for CPI-U (All items)
# Note: bls.gov API is limited to 20 requests per day for unregistered users

# CPI value for June 1994
june_94_cpi = 148.0

# Get WiFi details, ensure these are setup in settings.toml
ssid = os.getenv("CIRCUITPY_WIFI_SSID")
password = os.getenv("CIRCUITPY_WIFI_PASSWORD")

# Initalize Wifi, Socket Pool, Request Session
pool = adafruit_connection_manager.get_radio_socketpool(wifi.radio)
ssl_context = adafruit_connection_manager.get_radio_ssl_context(wifi.radio)
requests = adafruit_requests.Session(pool, ssl_context)

try:
    # Connect to the WiFi network
    wifi.radio.connect(ssid, password)
except OSError as ose:
    print(f"OSError: {ose}")
print("Wifi connected!")

# Get display reference
display = supervisor.runtime.display

# Set to portrait orientation
display.rotation = 0

# Group to hold all visual elements
main_group = Group()

# Full display sized white background
white_bg_group = Group(scale=8)
white_bg_bmp = displayio.Bitmap(display.width // 8, display.height // 8, 1)
white_bg_palette = displayio.Palette(1)
white_bg_palette[0] = 0xFFFFFF
white_bg_tg = TileGrid(bitmap=white_bg_bmp, pixel_shader=white_bg_palette)
white_bg_group.append(white_bg_tg)
main_group.append(white_bg_group)

# 50 Cent photo
photo_bmp = OnDiskBitmap("50_cent.bmp")
photo_tg = TileGrid(bitmap=photo_bmp, pixel_shader=photo_bmp.pixel_shader)
main_group.append(photo_tg)


def get_latest_cpi_value():
    """
    Fetch the latest CPI data from BLS API.

    :return: tuple containing (latest CPI value, month, year)
    """
    try:
        response = requests.get(latest_cpi_url)
        try:
            json_data = response.json()
        except json.decoder.JSONDecodeError as json_error:
            raise Exception(f"JSON Parse error: {response.text}") from json_error

        latest_data = json_data["Results"]["series"][0]["data"][0]

        return (
            float(latest_data["value"]),
            latest_data["periodName"],
            latest_data["year"],
        )

    except Exception as e:
        raise Exception(f"Error fetching data from BLS API: {e}") from e


# fetch the latest CPI data
latest_cpi_value, month, year = get_latest_cpi_value()

# Label for the message below the photo
message_lbl = TextBox(
    FONT,
    128,
    TextBox.DYNAMIC_HEIGHT,
    align=TextBox.ALIGN_CENTER,
    text=f"As of {month} {year}\n50 Cent is worth",
    color=0x000000,
    scale=1,
)
message_lbl.anchor_point = (0, 0)
message_lbl.anchored_position = (0, photo_tg.tile_height + 6)
main_group.append(message_lbl)

# calculate current value of 50 cents from 1994
current_value = round(50.0 * (latest_cpi_value / june_94_cpi) + 0.5)

# Label for the calculated value
amount_lbl = TextBox(
    FONT,
    128 // 3,
    TextBox.DYNAMIC_HEIGHT,
    align=TextBox.ALIGN_CENTER,
    text=f"{current_value}",
    color=0x000000,
    scale=3,
)
amount_lbl.anchor_point = (0, 0)
amount_lbl.anchored_position = (0, photo_tg.tile_height + message_lbl.height + 12)
main_group.append(amount_lbl)

# Cent label at bottom of display
cent_lbl = TextBox(
    FONT,
    128,
    TextBox.DYNAMIC_HEIGHT,
    align=TextBox.ALIGN_CENTER,
    text="Cent",
    color=0x000000,
    scale=1,
)
cent_lbl.anchor_point = (0, 1)
cent_lbl.anchored_position = (0, display.height - 2)
main_group.append(cent_lbl)

# set main_group showing on the display
display.root_group = main_group
display.refresh()

# Sleep for 1 day
al = alarm.time.TimeAlarm(monotonic_time=time.monotonic() + 86400)
alarm.exit_and_deep_sleep_until_alarms(al)
# Does not return. Exits, and restarts after 1 day
