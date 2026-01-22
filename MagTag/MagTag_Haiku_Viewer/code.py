# SPDX-FileCopyrightText: 2025 Tim C, written for Adafruit Industries
#
# SPDX-License-Identifier: MIT
"""
MagTag Haiku Viewer

Displays haikus loaded from the haikus.txt file and/or the
AdafruitIO feed 'haikus'. Press left and right buttons to
cycle through the avialble haikus. Press the D12 button
to change to a new random haiku.
"""
import os
import random
import time

import bitmaptools
import board
import digitalio
import displayio
import supervisor
import wifi

from adafruit_io.adafruit_io import IO_HTTP, AdafruitIO_RequestError
from adafruit_bitmap_font import bitmap_font
import adafruit_connection_manager
from adafruit_debouncer import Debouncer
from adafruit_display_text.bitmap_label import Label
import adafruit_imageload
import adafruit_requests


# AdafruitIO connection. Will stay None if no WIFI or AIO credentials in settings.toml
io = None

# list of all haikus collected from the local file and
# ones pulled from 'haikus' feed on Adafruit IO
all_haikus = []

# If the WIFI is auto connected from web workflow
if wifi.radio.connected:
    # Check for AdafruitIO credentials in settings.toml
    aio_username = os.getenv("ADAFRUIT_AIO_USERNAME")
    aio_key = os.getenv("ADAFRUIT_AIO_KEY")

    # if there are AIO credentials
    if None not in {aio_username, aio_key}:
        # Initialize connection_manager and requests
        pool = adafruit_connection_manager.get_radio_socketpool(wifi.radio)
        ssl_context = adafruit_connection_manager.get_radio_ssl_context(wifi.radio)
        requests = adafruit_requests.Session(pool, ssl_context)
        # Initialize an Adafruit IO HTTP API object
        io = IO_HTTP(aio_username, aio_key, requests)

# if the AdafruitIO connection is active
if io is not None:
    try:
        # Connect to the haikus IO feed
        haiku_feed = io.get_feed("haikus")
        # Retrieve data value from the feed
        print("Retrieving data from haiku feed...")
        haikus_data_from_io = io.receive_all_data(haiku_feed["key"])

        # add the fetched haikus to the list
        for haiku_data in haikus_data_from_io:
            # replace escaped double slash newlines with single slash newline
            all_haikus.append(haiku_data["value"].replace("\\n", "\n"))
    except AdafruitIO_RequestError as re:
        print("No haikus feed found on AdafruitIO. Using local haikus.txt file only.")


# attempt to load hakus from local file
try:
    with open("haikus.txt", "r") as f:
        haiku_txt_file_content = f.read()

        # add all the haikus from the file to the list
        for haiku in haiku_txt_file_content.split("\n\n"):
            all_haikus.append(haiku)
except OSError as e:
    print("No haikus.txt file found.")

# make sure there is at least one haiku to show
if len(all_haikus) == 0:
    raise ValueError(
        "\nNo haikus were found.\nPlease add haikus to IO\nor the haikus file."
    )

print(f"Choosing from {len(all_haikus)} haikus")
# index of haiku to show. start on a random one
current_index = random.randint(0, len(all_haikus) - 1)

# get the selected haiku from the list
haiku = all_haikus[current_index]

# variable to hold the built-in eInk display reference
display = supervisor.runtime.display

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


# Bamboo image element across the bottom
bamboo_bmp, bamboo_palette = adafruit_imageload.load("bamboo.bmp")
bamboo_tg = displayio.TileGrid(bitmap=bamboo_bmp, pixel_shader=bamboo_palette)
bamboo_tg.y = display.height - bamboo_tg.tile_height - 5
main_group.append(bamboo_tg)

# Grey border around the edges of the display
border_group = displayio.Group(scale=4)
border_bmp = displayio.Bitmap(display.width // 4, display.height // 4, 1)
border_palette = displayio.Palette(2)
border_palette[0] = 0x999999
border_palette[1] = 0xFFFFFF
border_palette.make_transparent(1)
bitmaptools.fill_region(
    border_bmp, 1, 1, border_bmp.width - 1, border_bmp.height - 1, 1
)
border_tg = displayio.TileGrid(border_bmp, pixel_shader=border_palette)
border_group.append(border_tg)
main_group.append(border_group)

# load the custom font & initialze Label to show haiku
FONT = bitmap_font.load_font("fanwood_webfont_15.bdf", displayio.Bitmap)
haiku_lbl = Label(FONT, text=haiku, scale=1, color=0x333333, line_spacing=1.0)
haiku_lbl.anchor_point = (0, 0)
haiku_lbl.anchored_position = (8, 0)
main_group.append(haiku_lbl)

# set up left button pin and debouncer
left_btn_pin = digitalio.DigitalInOut(board.D15)
left_btn_pin.direction = digitalio.Direction.INPUT
left_btn_pin.pull = digitalio.Pull.UP
left_btn = Debouncer(left_btn_pin)

# set up right button pin and debouncer
right_btn_pin = digitalio.DigitalInOut(board.D11)
right_btn_pin.direction = digitalio.Direction.INPUT
right_btn_pin.pull = digitalio.Pull.UP
right_btn = Debouncer(right_btn_pin)

# setup D12 button and debouncer
random_btn_pin = digitalio.DigitalInOut(board.D12)
random_btn_pin.direction = digitalio.Direction.INPUT
random_btn_pin.pull = digitalio.Pull.UP
random_btn = Debouncer(random_btn_pin)

# set main_group as root_group to show on the display
display.root_group = main_group


def refresh_display():
    """
    Wait until the display is ready to refresh,
    and then call refresh() on it.
    :return:
    """
    time.sleep(display.time_to_refresh)
    display.refresh()


# initial refresh to show the first haiku
refresh_display()

# main loop
while True:
    # update the button debouncers
    right_btn.update()
    left_btn.update()
    random_btn.update()

    # if the right button was pressed
    if right_btn.fell:
        print("right button pressed")
        # increment the current index
        current_index += 1
        # wrap around if past len of the list
        if current_index >= len(all_haikus):
            current_index = 0
        # get the new haiku
        haiku = all_haikus[current_index % len(all_haikus)]
        # set the new haiku text on the Label
        haiku_lbl.text = haiku
        refresh_display()

    # if the left button was pressed
    if left_btn.fell:
        print("left button pressed")
        # decrement the current index
        current_index -= 1
        # wrap around if below 0
        if current_index < 0:
            current_index = len(all_haikus) - 1
        # get the new haiku
        haiku = all_haikus[current_index % len(all_haikus)]
        # set the new haiku text on the Label
        haiku_lbl.text = haiku
        refresh_display()

    # if the (D12) random button was pressed
    if random_btn.fell:
        # ensure at least 2 haikus for random function
        if len(all_haikus) > 1:
            # choose a random haiku, different from currently showing one
            old_index = current_index
            while current_index == old_index:
                current_index = random.randint(0, len(all_haikus) - 1)

            # get the new haiku
            haiku = all_haikus[current_index % len(all_haikus)]
            # set the new haiku text on the Label
            haiku_lbl.text = haiku
            refresh_display()
