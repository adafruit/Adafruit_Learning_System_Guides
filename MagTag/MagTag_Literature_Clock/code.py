# SPDX-FileCopyrightText: 2025 Tim C, written for Adafruit Industries
#
# SPDX-License-Identifier: MIT
"""
Literature Quotes Clock for the Adafruit MagTag

This project displays the current time by showing a quote from a book
that references the time. Every minute of the day has a different quote.
The current time reference portion of the quote is accented with an outline
to make it easier to see at a glance.

This project was inspired by:
 - https://github.com/JohannesNE/literature-clock
 - https://www.instructables.com/Literary-Clock-Made-From-E-reader/

The quotes were sourced originally by The Guardian:
https://www.theguardian.com/books/table/2011/apr/21/literary-clock?CMP=twt_gu
"""
import os
import random
import time
import zlib

import displayio
import rtc
import socketpool
import supervisor
import terminalio
import wifi

import adafruit_ntp
from adafruit_display_text.bitmap_label import Label
from adafruit_display_text import wrap_text_to_pixels

# Set the current offset for your timezone
TZ_OFFSET_FROM_UTC = -6


def which_line_contains(all_lines, important_passage):
    """
    Find the line that contains the important passage
    :param all_lines: The lines to search
    :param important_passage: The passage to search for
    :return: The index of the line that contains the important passage
      or None if it was not found
    """

    index_within_spaced_version = " ".join(all_lines).find(important_passage)

    working_index = 0
    for i in range(len(all_lines)):
        line = all_lines[i]
        if working_index <= index_within_spaced_version < working_index + len(line):
            return i
        working_index += len(line) + 1  # extra 1 for the newline

    return None


def find_lines_to_show(all_lines, important_passage):
    """
    Find the line that contains ``important_passage`` and return
    the start of the range of 7 lines that provides the largest possible
    context around it.

    :param all_lines: The lines to search
    :param important_passage: The passage to search for
    :return: index of the first line in a range of 7 lines with the widest context.
    """
    if len(all_lines) <= 7:
        return 0

    try:
        passage_line = which_line_contains(all_lines, important_passage)
        if passage_line <= 3:
            return 0
    except TypeError as e:
        raise TypeError(f"ip: {important_passage} | {all_lines}") from e

    if passage_line >= len(all_lines) - 4:
        return len(all_lines) - 7

    return passage_line - 3


display = supervisor.runtime.display

# WIFI Setup
wifi_ssid = os.getenv("CIRCUITPY_WIFI_SSID")
wifi_password = os.getenv("CIRCUITPY_WIFI_PASSWORD")
if wifi_ssid is None:
    print("WiFi credentials are kept in settings.toml, please add them there!")
    raise ValueError("SSID not found in environment variables")

try:
    wifi.radio.connect(wifi_ssid, wifi_password)
except ConnectionError:
    print("Failed to connect to WiFi with provided credentials")
    raise

# Wait a few seconds for WIFI to finish connecting and be ready
time.sleep(2)

# Fetch time from NTP
pool = socketpool.SocketPool(wifi.radio)
ntp = adafruit_ntp.NTP(
    pool,
    server="0.adafruit.pool.ntp.org",
    tz_offset=TZ_OFFSET_FROM_UTC,
    cache_seconds=3600,
)

# Update the system RTC from the NTP time
rtc.RTC().datetime = ntp.datetime

# main group to hold all other visual elements
main_group = displayio.Group()

# background group used for white background behind the quote
# scale 8x to save memory on the Bitmap
bg_group = displayio.Group(scale=8)

# Create & append Bitmap for the white background
bg_bmp = displayio.Bitmap(display.width // 8, display.height // 8, 1)
bg_palette = displayio.Palette(1)
bg_palette[0] = 0xFFFFFF
bg_tg = displayio.TileGrid(bg_bmp, pixel_shader=bg_palette)
bg_group.append(bg_tg)
main_group.append(bg_group)

# Setup accent palette for the outlined text
accent_palette = displayio.Palette(5)
accent_palette[3] = 0x666666
accent_palette[4] = 0xFFFFFF

# Setup BitmapLabel to show the quote
quote_lbl = Label(
    terminalio.FONT, text="", color=0x666666, color_palette=accent_palette
)
quote_lbl.anchor_point = (0, 0)
quote_lbl.anchored_position = (2, 2)
main_group.append(quote_lbl)

# Setup BitmapLabel to show book title and author
book_info_lbl = Label(terminalio.FONT, text="", color=0x666666)
book_info_lbl.anchor_point = (0, 1.0)  # place it at the bottom of the display
book_info_lbl.anchored_position = (2, display.height - 2)
main_group.append(book_info_lbl)

# Set main group containing visual elements to show on the display
display.root_group = main_group

while True:
    # get the current time from system RTC
    now = time.localtime()

    # break out the current hour in 24hr format
    hour = f"{now.tm_hour:02d}"

    # open the data file for the current hour
    with open(f"split_data_compressed/{hour}.csv.gz", "rb") as f:
        # read and unzip the data
        compressed_data = f.read()
        rows = zlib.decompress(compressed_data).split(b"\n")

    # break out the current minute
    current_minute = f"{now.tm_min:02d}".encode("utf-8")

    print(f"hour: {hour} min: {current_minute}")

    # list to hold possible quotes for the current time
    options = []

    # get the previous minute also for alternate choices
    previous_minute = f"{now.tm_min - 1:02d}".encode("utf-8")
    # list to hold alternate choices
    alternates = []

    # loop over all rows in the data from the CSV
    for row in rows:
        # if the current row is for the current time
        if row[3:5] == current_minute:
            # add the current row as a potential choice to show
            options.append(row)

        # if the current row is for the previous minute
        if row[3:5] == previous_minute:
            # add the current row as an alternate choice
            alternates.append(row)

    # if there is at least one option for the current time
    if len(options) > 0:
        # make a random choice from the possible quote options
        choice = random.choice(options)

    else:  # No options for current time
        # use a random choice from the previous minute instead
        choice = random.choice(alternates)

    # decode the row of data from bytes to a string
    row_str = choice.decode("utf-8")

    # split the data on the pipe character
    parts = row_str.split("|")

    # extract the quote text
    quote = parts[2]

    # extract the author
    author = parts[4]

    # extract the book title
    title = parts[3]

    # set the text in the book info label to show the title and author
    book_info_lbl.text = f"{title} - {author}"

    # extract the current time reference string
    time_part = parts[1]

    # get start and end indexes of the time reference
    time_start_index = quote.find(time_part)
    time_end_index = time_start_index + len(time_part)

    # split the quote text into lines with a maximum width that fits
    # on the MagTag display
    quote_lines = wrap_text_to_pixels(
        quote,
        display.width - 4,
        terminalio.FONT,
        outline_accent_ranges=[
            (time_start_index, time_end_index, quote_lbl.outline_size)
        ],
    )

    # remove previous accents
    quote_lbl.clear_accent_ranges()

    # find the index of the first line we want to show.
    # only relevant for long quotes, short ones will be shown in full
    first_line_to_show = find_lines_to_show(quote_lines, time_part)

    # Temporary version of final visible quote joined with spaces instead of newlines,
    # so we can search for the time_part without worrying about potential newlines.
    shown_quote_with_spaces = " ".join(
        quote_lines[first_line_to_show : first_line_to_show + 7]
    )

    # find the current time reference within the quote that will be shown
    time_start_index = shown_quote_with_spaces.find(time_part)
    time_end_index = time_start_index + len(time_part)

    # wrap the quote to be shown to multiple lines and set it on the label
    quote_lbl.text = "\n".join(quote_lines[first_line_to_show : first_line_to_show + 7])

    # accent the part of the quote that references the current time
    quote_lbl.add_accent_range(time_start_index, time_end_index, 4, 3, "outline")

    # update the display and wait 60 seconds
    display.refresh()
    time.sleep(60)
