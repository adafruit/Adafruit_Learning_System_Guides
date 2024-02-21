# SPDX-FileCopyrightText: 2019 Carter Nelson for Adafruit Industries
#
# SPDX-License-Identifier: MIT

import time
import board
from adafruit_pyportal import PyPortal
from adafruit_bitmap_font import bitmap_font
from adafruit_display_text.label import Label

# --| USER CONFIG |--------------------------
STATION_ID = (
    "9447130"  # tide location, find yours here: https://tidesandcurrents.noaa.gov/
)
HI_COLOR = 0x00FF00  # high tide times color
LO_COLOR = 0x11FFFF  # low tide times color
DATE_COLOR = 0xFFFFFF  # date and time color
# -------------------------------------------

# pylint: disable=line-too-long
DATA_SOURCE = (
    "https://api.tidesandcurrents.noaa.gov/api/prod/datagetter?date=today&product=predictions&datum=mllw&interval=hilo&format=json&units=metric&time_zone=lst_ldt&station="
    + STATION_ID
)
DATA_LOCATION = ["predictions"]

# gotta have one of these
pyportal = PyPortal(status_neopixel=board.NEOPIXEL, default_bg="/images/tides_bg.bmp")

# Connect to the internet and get local time
pyportal.get_local_time()

# Setup tide times font
tide_font = bitmap_font.load_font("/fonts/cq-mono-30.bdf")
tide_font.load_glyphs(b"1234567890:")

# Setup date and time font
date_font = bitmap_font.load_font("/fonts/Arial-12.bdf")
date_font.load_glyphs(b"1234567890-")

# Labels setup
HI_LABELS = [
    Label(tide_font, text="00:00", color=HI_COLOR, x=40, y=80),
    Label(tide_font, text="00:00", color=HI_COLOR, x=40, y=165),
]
LO_LABELS = [
    Label(tide_font, text="00:00", color=LO_COLOR, x=180, y=80),
    Label(tide_font, text="00:00", color=LO_COLOR, x=180, y=165),
]
DATE_LABEL = Label(date_font, text="0000-00-00 00:00:00", color=DATE_COLOR, x=75, y=228)

# Add all the labels to the display
for label in HI_LABELS + LO_LABELS + [DATE_LABEL]:
    pyportal.graphics.splash.append(label)


def get_tide_info():
    """Fetch JSON tide time info and return it."""

    # Get raw JSON data
    raw_info = pyportal.network.fetch_data(DATA_SOURCE, json_path=DATA_LOCATION)

    # Return will be a dictionary of lists containing tide times
    new_tide_info = {"H": [], "L": []}

    # Parse out the tide time info
    for info in raw_info[0]:
        tide_type = info["type"]
        tide_time = info["t"].split(" ")[1]
        new_tide_info[tide_type].append(tide_time)

    return new_tide_info


def update_display(time_info, update_tides=False):
    """Update the display with current info."""

    # Tide time info
    if update_tides:
        # out with the old
        for tide_label in HI_LABELS + LO_LABELS:
            tide_label.text = ""
        # in with the new
        for i, hi_time in enumerate(tide_info["H"]):
            HI_LABELS[i].text = hi_time
        for i, lo_time in enumerate(tide_info["L"]):
            LO_LABELS[i].text = lo_time

    # Date and time
    DATE_LABEL.text = "{:04}-{:02}-{:02} {:02}:{:02}:{:02}".format(
        time_info.tm_year,
        time_info.tm_mon,
        time_info.tm_mday,
        time_info.tm_hour,
        time_info.tm_min,
        time_info.tm_sec,
    )


# First run update
tide_info = get_tide_info()
current_time = time.localtime()
update_display(current_time, True)
current_yday = current_time.tm_yday

# Update daily
while True:
    current_time = time.localtime()
    new_tides = False
    if current_time.tm_yday != current_yday:
        # new day, time to update
        tide_info = get_tide_info()
        new_tides = True
        current_yday = current_time.tm_yday
    update_display(current_time, new_tides)
    time.sleep(0.5)
