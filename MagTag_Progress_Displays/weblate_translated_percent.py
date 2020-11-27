# SPDX-FileCopyrightText: 2020 Tim C, written for Adafruit Industries
#
# SPDX-License-Identifier: Unlicense
"""
Pull the current translated percent of CircuitPython
from Weblate and show it on the screen with text
and a progress bar
"""
import time
import terminalio
from adafruit_magtag.magtag import MagTag
from adafruit_progressbar import ProgressBar

time.sleep(4)
# Set up where we'll be fetching data from
DATA_SOURCE = "https://hosted.weblate.org/api/projects/circuitpython/statistics/"
DATA_LOCATION = ["translated_percent"]


def text_transform(val):
    return "Translated: {}%".format(val)


magtag = MagTag(
    url=DATA_SOURCE,
    json_path=DATA_LOCATION,
)

magtag.network.connect()

magtag.add_text(
    text_font="fonts/leaguespartan18.bdf",
    text_position=(
        (magtag.graphics.display.width // 2) - 1,
        42,
    ),
    text_scale=1,
    text_transform=text_transform,
    text_anchor_point=(0.5, 0.5),
)

bottom_lbl_txt = "hosted.weblate.org/projects/circuitpython/"
magtag.add_text(
    text_font="fonts/leaguespartan11.bdf",
    text_position=(
        (magtag.graphics.display.width // 2) - 1,
        (magtag.graphics.display.height) - 8,
    ),
    text_scale=1,
    text_transform=text_transform,
    text_anchor_point=(0.5, 1.0),
    is_data=False,
)

top_lbl_txt = "CircuitPython"
magtag.add_text(
    text_font="fonts/leaguespartan18.bdf",
    text_position=(
        (magtag.graphics.display.width // 2) - 1,
        16,
    ),
    text_scale=1,
    text_transform=text_transform,
    text_anchor_point=(0.5, 0.5),
    is_data=False,
)

magtag.set_text(bottom_lbl_txt, index=1)
magtag.set_text(top_lbl_txt, index=2)
# set progress bar width and height relative to board's display
BAR_WIDTH = magtag.graphics.display.width - 80
BAR_HEIGHT = 30

BAR_X = magtag.graphics.display.width // 2 - BAR_WIDTH // 2
BAR_Y = 66

# Create a new progress_bar object at (x, y)
progress_bar = ProgressBar(
    BAR_X, BAR_Y, BAR_WIDTH, BAR_HEIGHT, 1.0, bar_color=0x999999, outline_color=0x000000
)

magtag.graphics.splash.append(progress_bar)

timestamp = None

while True:
    if (
        not timestamp or (time.monotonic() - timestamp) > 600
    ):  # once every 600 seconds...
        try:
            value = magtag.fetch()
            print("Response is", value)
            time.sleep(5)
            progress_bar.progress = value / 100.0
            magtag.refresh()
        except (ValueError, RuntimeError) as e:
            print("Some error occured, retrying! -", e)
        timestamp = time.monotonic()
