# SPDX-FileCopyrightText: 2022 Charlyn Gonda for Adafruit Industries
#
# SPDX-License-Identifier: MIT
from secrets import secrets
import ssl
import busio
import board
import adafruit_lis3dh
import wifi
import socketpool
import adafruit_requests

from adafruit_led_animation.color import (
    PURPLE, AMBER, JADE, CYAN, BLUE, GOLD, PINK)
from adafruit_io.adafruit_io import IO_HTTP

from cube import Cube

# Specify pins
top_cin = board.A0
top_din = board.A1
side_panels_cin = board.A2
side_panels_din = board.A3
bottom_cin = board.A4
bottom_din = board.A5

# Initialize cube with pins
cube = Cube(top_cin,
            top_din,
            side_panels_cin,
            side_panels_din,
            bottom_cin,
            bottom_din)

# Initial display to indicate the cube is on
cube.waiting_mode()

# Setup for Accelerometer
i2c = busio.I2C(board.SCL1, board.SDA1)
lis3dh = adafruit_lis3dh.LIS3DH_I2C(i2c)

connected = False
while not connected:
    try:
        wifi.radio.connect(secrets["ssid"], secrets["password"])
        print("Connected to %s!" % secrets["ssid"])
        print("My IP address is", wifi.radio.ipv4_address)
        connected = True
    # pylint: disable=broad-except
    except Exception as error:
        print(error)
        connected = False


# Setup for http requests
pool = socketpool.SocketPool(wifi.radio)
REQUESTS = adafruit_requests.Session(pool, ssl.create_default_context())
IO = IO_HTTP(secrets["aio_username"], secrets["aio_key"], REQUESTS)

# Data for top pixels, will be updated by update_data()
TOP_PIXELS_ON = []
TOP_PIXELS_COLOR = CYAN
TOP_PIXELS_COLOR_MAP = {
    "PURPLE": PURPLE,
    "AMBER": AMBER,
    "JADE": JADE,
    "CYAN": CYAN,
    "BLUE": BLUE,
    "GOLD": GOLD,
    "PINK": PINK,
}
# Data for scrolling word, will be updated by update_data()
CUBE_WORD = "... ..."


def update_data():
    # pylint: disable=global-statement
    global CUBE_WORD, TOP_PIXELS_ON, TOP_PIXELS_COLOR
    if connected:
        print("Updating data from Adafruit IO")
        try:
            quote_feed = IO.get_feed('cube-words')
            quotes_data = IO.receive_data(quote_feed["key"])
            CUBE_WORD = quotes_data["value"]

            pixel_feed = IO.get_feed('cube-pixels')
            pixel_data = IO.receive_data(pixel_feed["key"])
            color, pixels_list = pixel_data["value"].split("-")
            TOP_PIXELS_ON = pixels_list.split(",")
            TOP_PIXELS_COLOR = TOP_PIXELS_COLOR_MAP[color]
        # pylint: disable=broad-except
        except Exception as update_error:
            print(update_error)


orientations = [
    "UP",
    "DOWN",
    "RIGHT",
    "LEFT",
    "FRONT",
    "BACK"
]

# pylint: disable=inconsistent-return-statements


def orientation(curr_x, curr_y, curr_z):
    absX = abs(curr_x)
    absY = abs(curr_y)
    absZ = abs(curr_z)

    if absX > absY and absX > absZ:
        if x >= 0:
            return orientations[1]  # up

        return orientations[0]  # down

    if absZ > absY and absZ > absX:  # when "down" is "up"
        if z >= 0:
            return orientations[2]  # left

        return orientations[3]  # right

    if absY > absX and absY > absZ:
        if y >= 0:
            return orientations[4]  # front

        return orientations[5]  # back


upside_down = False
while True:
    x, y, z = lis3dh.acceleration
    oriented = orientation(x, y, z)

    # clear cube when on one side
    # this orientation can be used while charging
    if oriented == orientations[5]:  # "back" side
        cube.clear_cube(True)
        continue

    if oriented == orientations[1]:
        upside_down = True
    else:
        upside_down = False

    if not upside_down:
        if cube.done_scrolling:
            update_data()

        cube.update(CUBE_WORD, TOP_PIXELS_COLOR, TOP_PIXELS_ON)
        cube.scroll_word_and_update_top()

    else:
        cube.upside_down_mode()
