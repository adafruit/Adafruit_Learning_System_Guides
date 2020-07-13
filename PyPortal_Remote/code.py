# SPDX-FileCopyrightText: 2019 ladyada for Adafruit Industries
# SPDX-License-Identifier: MIT

import time
import math
import board
import busio
from digitalio import DigitalInOut
import neopixel
from adafruit_esp32spi import adafruit_esp32spi
from adafruit_esp32spi import adafruit_esp32spi_wifimanager
import displayio
import adafruit_touchscreen
import adafruit_imageload

# Set up the touchscreen
ts = adafruit_touchscreen.Touchscreen(
    board.TOUCH_XL,
    board.TOUCH_XR,
    board.TOUCH_YD,
    board.TOUCH_YU,
    calibration=((5200, 59000), (5800, 57000)),
    size=(320, 240),
)

# Get wifi details and more from a secrets.py file
try:
    from secrets import secrets
except ImportError:
    print("WiFi secrets are kept in secrets.py, please add them there!")
    raise

# If you are using a board with pre-defined ESP32 Pins:
esp32_cs = DigitalInOut(board.ESP_CS)
esp32_ready = DigitalInOut(board.ESP_BUSY)
esp32_reset = DigitalInOut(board.ESP_RESET)

spi = busio.SPI(board.SCK, board.MOSI, board.MISO)
esp = adafruit_esp32spi.ESP_SPIcontrol(spi, esp32_cs, esp32_ready, esp32_reset)

status_light = neopixel.NeoPixel(board.NEOPIXEL, 1, brightness=0.2)

wifi = adafruit_esp32spi_wifimanager.ESPSPI_WiFiManager(esp, secrets, status_light)

# Set the ip of your Roku here
ip = "192.168.1.3"

"""
Possible keypress key values to send the Roku
Home
Rev
Fwd
Play
Select
Left
Right
Down
Up
Back
InstantReplay
Info
Backspace
Search
Enter
FindRemote

Keypress key values that only work on smart TVs with built-in Rokus
VolumeDown
VolumeMute
VolumeUp
PowerOff
ChannelUp
ChannelDown
"""


def getchannels():
    """ Gets the channels installed on the device. Also useful because it
        verifies that the PyPortal can see the Roku"""
    try:
        print("Getting channels. Usually takes around 10 seconds...", end="")
        response = wifi.get("http://{}:8060/query/apps".format(ip))
        channel_dict = {}
        for i in response.text.split("<app")[2:]:
            a = i.split("=")
            chan_id = a[1].split('"')[1]
            name = a[-1].split(">")[1].split("<")[0]
            channel_dict[name] = chan_id
        response.close()
        return channel_dict
    except (ValueError, RuntimeError) as e:
        print("Failed to get data\n", e)
        wifi.reset()
        return None
    response = None
    return None


def sendkey(key):
    """ Sends a key to the Roku """
    try:
        print("Sending key: {}...".format(key), end="")
        response = wifi.post("http://{}:8060/keypress/{}".format(ip, key))
        if response:
            response.close()
            print("OK")
    except (ValueError, RuntimeError) as e:
        print("Failed to get data\n", e)
        wifi.reset()
        return
    response = None


def sendletter(letter):
    """ Sends a letter to the Roku, not used in this guide """
    try:
        print("Sending letter: {}...".format(letter), end="")
        response = wifi.post("http://{}:8060/keypress/lit_{}".format(ip, letter))
        if response:
            response.close()
            print("OK")
    except (ValueError, RuntimeError) as e:
        print("Failed to get data\n", e)
        wifi.reset()
        return
    response = None


def openchannel(channel):
    """ Tells the Roku to open the channel with the corresponding channel id """
    try:
        print("Opening channel: {}...".format(channel), end="")
        response = wifi.post("http://{}:8060/launch/{}".format(ip, channel))
        if response:
            response.close()
            print("OK")
        response = None
    except (ValueError, RuntimeError):
        print("Probably worked")
        wifi.reset()
    response = None


def switchpage(tup):
    """ Used to switch to a different page """
    p_num = tup[0]
    tile_grid = tup[1]
    new_page = pages[p_num - 1]
    new_page_vals = pages_vals[p_num - 1]
    my_display_group[-1] = tile_grid
    return new_page, new_page_vals


# Verifies the Roku and Pyportal are connected and visible
channels = getchannels()

my_display_group = displayio.Group(max_size=25)

image_1, palette_1 = adafruit_imageload.load(
    "images/page_1.bmp", bitmap=displayio.Bitmap, palette=displayio.Palette
)
tile_grid_1 = displayio.TileGrid(image_1, pixel_shader=palette_1)
my_display_group.append(tile_grid_1)

image_2, palette_2 = adafruit_imageload.load(
    "images/page_2.bmp", bitmap=displayio.Bitmap, palette=displayio.Palette
)
tile_grid_2 = displayio.TileGrid(image_2, pixel_shader=palette_2)

image_3, palette_3 = adafruit_imageload.load(
    "images/page_3.bmp", bitmap=displayio.Bitmap, palette=displayio.Palette
)
tile_grid_3 = displayio.TileGrid(image_3, pixel_shader=palette_3)

# fmt: off
# Page 1
page_1 = [sendkey, sendkey, sendkey,
          sendkey, sendkey, sendkey,
          sendkey, sendkey, sendkey,
          sendkey, sendkey, switchpage]

page_1_vals = ["Back", "Up", "Home",
               "Left", "Select", "Right",
               "Search", "Down", "Info",
               "Rev", "Play", (2, tile_grid_2)]

# Page 2
page_2 = [openchannel, openchannel, openchannel,
          openchannel, openchannel, openchannel,
          openchannel, openchannel, openchannel,
          switchpage, sendkey, switchpage]

page_2_vals = [14362, 2285, 13,
               12, 8378, 837,
               38820, 47389, 7767,
               (1, tile_grid_1), "Home", (3, tile_grid_3)]

page_3 = [None, None, None,
          sendkey, None, sendkey,
          sendkey, sendkey, sendkey,
          switchpage, sendkey, sendkey]

page_3_vals = [None, None, None,
               "Search", None, "Info",
               "Rev", "Play", "Fwd",
               (2, tile_grid_2), "Back", "Home"]
# fmt: on

pages = [page_1, page_2, page_3]
pages_vals = [page_1_vals, page_2_vals, page_3_vals]

page = page_1
page_vals = page_1_vals

board.DISPLAY.show(my_display_group)
print("READY")


last_index = 0
while True:
    p = ts.touch_point
    if p:
        x = math.floor(p[0] / 80)
        y = abs(math.floor(p[1] / 80) - 2)
        index = 3 * x + y
        # Used to prevent the touchscreen sending incorrect results
        if last_index == index:
            if page[index]:
                # pylint: disable=comparison-with-callable
                if page[index] == switchpage:
                    page, page_vals = switchpage(page_vals[index])
                else:
                    page[index](page_vals[index])
                time.sleep(0.1)

        last_index = index
