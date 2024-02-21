# SPDX-FileCopyrightText: 2019 Carter Nelson for Adafruit Industries
#
# SPDX-License-Identifier: MIT

import time
import board
import displayio
from adafruit_pyportal import PyPortal
from adafruit_bitmap_font import bitmap_font
from adafruit_display_text.label import Label

# --| USER CONFIG |--------------------------
STATION_ID = (
    "9447130"  # tide location, find yours here: https://tidesandcurrents.noaa.gov/
)
PLOT_SIZE = 2  # tide plot thickness
PLOT_COLOR = 0x00FF55  # tide plot color
MARK_SIZE = 6  # current time marker size
MARK_COLOR = 0xFF0000  # current time marker color
DATE_COLOR = 0xE0CD1A  # date text color
TIME_COLOR = 0xE0CD1A  # time text color
VSCALE = 20  # vertical plot scale
# -------------------------------------------

# pylint: disable=line-too-long
DATA_SOURCE = (
    "https://api.tidesandcurrents.noaa.gov/api/prod/datagetter?date=today&product=predictions&datum=mllw&format=json&units=metric&time_zone=lst_ldt&station="
    + STATION_ID
)
DATA_LOCATION = ["predictions"]

WIDTH = board.DISPLAY.width
HEIGHT = board.DISPLAY.height

# gotta have one of these
pyportal = PyPortal(status_neopixel=board.NEOPIXEL, default_bg="/images/tides_bg_graph.bmp")

# Connect to the internet and get local time
pyportal.get_local_time()

# Setup palette used for plot
palette = displayio.Palette(3)
palette[0] = 0x0
palette[1] = PLOT_COLOR
palette[2] = MARK_COLOR
palette.make_transparent(0)

# Setup tide plot bitmap
tide_plot = displayio.Bitmap(WIDTH, HEIGHT, 3)
pyportal.graphics.splash.append(displayio.TileGrid(tide_plot, pixel_shader=palette))

# Setup font used for date and time
date_font = bitmap_font.load_font("/fonts/mono-bold-8.bdf")
date_font.load_glyphs(b"1234567890-")

# Setup date label
date_label = Label(date_font, text="0000-00-00", color=DATE_COLOR, x=7, y=14)
pyportal.graphics.splash.append(date_label)

# Setup time label
time_label = Label(date_font, text="00:00:00", color=TIME_COLOR, x=234, y=14)
pyportal.graphics.splash.append(time_label)

# Setup current time marker
time_marker_bitmap = displayio.Bitmap(MARK_SIZE, MARK_SIZE, 3)
time_marker_bitmap.fill(2)
time_marker = displayio.TileGrid(
    time_marker_bitmap, pixel_shader=palette, x=-MARK_SIZE, y=-MARK_SIZE
)
pyportal.graphics.splash.append(time_marker)


def get_tide_data():
    """Fetch JSON tide data and return parsed results in a list."""

    # Get raw JSON data
    raw_data = pyportal.network.fetch_data(DATA_SOURCE, json_path=DATA_LOCATION)

    # Results will be stored in a list that is display WIDTH long
    new_tide_data = [None] * WIDTH

    # Convert raw data to display coordinates
    for data in raw_data[0]:
        _, t = data["t"].split(" ")  # date and time
        h, m = t.split(":")  # hours and minutes
        v = data["v"]  # water level
        x = round((WIDTH - 1) * (60 * float(h) + float(m)) / 1440)
        y = (HEIGHT // 2) - round(VSCALE * float(v))
        y = 0 if y < 0 else y
        y = HEIGHT - 1 if y >= HEIGHT else y
        new_tide_data[x] = y

    return new_tide_data


def draw_data_point(x, y, size=PLOT_SIZE, color=1):
    """Draw data point on to the tide plot bitmap at (x,y)."""
    if y is None:
        return
    offset = size // 2
    for xx in range(x - offset, x + offset + 1):
        for yy in range(y - offset, y + offset + 1):
            try:
                tide_plot[xx, yy] = color
            except IndexError:
                pass


def draw_time_marker(time_info):
    """Draw a marker on the tide plot for the current time."""
    h = time_info.tm_hour
    m = time_info.tm_min
    x = round((WIDTH - 1) * (60 * float(h) + float(m)) / 1440)
    y = tide_data[x]
    if y is not None:
        x -= MARK_SIZE // 2
        y -= MARK_SIZE // 2
        time_marker.x = x
        time_marker.y = y


def update_display(time_info, update_tides=False):
    """Update the display with current info."""

    # Tide data plot
    if update_tides:
        # out with the old
        for i in range(WIDTH * HEIGHT):
            tide_plot[i] = 0
        # in with the new
        for x in range(WIDTH):
            draw_data_point(x, tide_data[x])

    # Current location marker
    draw_time_marker(time_info)

    # Date and time
    date_label.text = "{:04}-{:02}-{:02}".format(
        time_info.tm_year, time_info.tm_mon, time_info.tm_mday
    )
    time_label.text = "{:02}:{:02}:{:02}".format(
        time_info.tm_hour, time_info.tm_min, time_info.tm_sec
    )


# First run update
tide_data = get_tide_data()
current_time = time.localtime()
update_display(current_time, True)
current_yday = current_time.tm_yday

# Run forever
while True:
    current_time = time.localtime()
    new_tides = False
    if current_time.tm_yday != current_yday:
        # new day, time to update
        tide_data = get_tide_data()
        new_tides = True
        current_yday = current_time.tm_yday
    update_display(current_time, new_tides)
    time.sleep(0.5)
