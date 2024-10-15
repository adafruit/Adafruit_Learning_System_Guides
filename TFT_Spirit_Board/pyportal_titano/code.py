# SPDX-FileCopyrightText: 2024 Tim Cocks
#
# SPDX-License-Identifier: MIT
"""
SpiritBoard code.py
PyPortal w/ 480x320 pixel display

Receive and display messages from the spirits.
"""
# pylint: disable=import-error, invalid-name

import os
import board
from digitalio import DigitalInOut
import adafruit_connection_manager
from adafruit_esp32spi import adafruit_esp32spi
import adafruit_touchscreen
import adafruit_requests
from adafruit_io.adafruit_io import IO_HTTP, AdafruitIO_RequestError

from spirit_board import SpiritBoard

display = board.DISPLAY

# Initialize the touch overlay
touchscreen = adafruit_touchscreen.Touchscreen(
    board.TOUCH_XL,
    board.TOUCH_XR,
    board.TOUCH_YD,
    board.TOUCH_YU,
    calibration=((6584, 59861), (9505, 57492)),
    size=(board.DISPLAY.width, board.DISPLAY.height),
)

# Initialize the ES32SPI Coprocessor
esp32_cs = DigitalInOut(board.ESP_CS)
esp32_ready = DigitalInOut(board.ESP_BUSY)
esp32_reset = DigitalInOut(board.ESP_RESET)
spi = board.SPI()
esp = adafruit_esp32spi.ESP_SPIcontrol(spi, esp32_cs, esp32_ready, esp32_reset)

# connect to wifi network defined in settings.toml
print("Connecting to AP...")

try:
    esp.connect_AP(os.getenv("CIRCUITPY_WIFI_SSID"), os.getenv("CIRCUITPY_WIFI_PASSWORD"))

    # Initialize a requests session
    pool = adafruit_connection_manager.get_radio_socketpool(esp)
    ssl_context = adafruit_connection_manager.get_radio_ssl_context(esp)
    requests = adafruit_requests.Session(pool, ssl_context)

    # Set your Adafruit IO Username and Key in secrets.py
    # (visit io.adafruit.com if you need to create an account,
    # or if you need your Adafruit IO key.)
    aio_username = os.getenv("AIO_USERNAME")
    aio_key = os.getenv("AIO_KEY")

    # Initialize an Adafruit IO HTTP API object
    io = IO_HTTP(aio_username, aio_key, requests)
except (RuntimeError, TypeError) as e:
    print("could not connect to AP or AdafruitIO: ", e)
    io = None

# initialize the SpiritBoard class
spirit_board = SpiritBoard(display)

# get messages from io or the local file
messages = spirit_board.get_messages(io)

# The planchette is already at the home position.
# Slide it to home again to make it jump, in order
# indicate the message is ready to be received.
spirit_board.slide_planchette(SpiritBoard.LOCATIONS["home"], delay=0.02, step_size=6)

# current message index
message_index = 0
while True:
    # read the touch screen
    p = touchscreen.touch_point

    # if the display was touched
    if p:
        # write the message at the current index
        spirit_board.write_message(messages[message_index], step_size=8)

        # if there are more messages in the list inside of context
        if message_index < len(messages) - 1:
            # increment the message index
            message_index += 1

        else:  # there are no more messages in the list
            # reset the index to 0
            message_index = 0
            print("fetching next")

            # fetch new messages
            messages = spirit_board.get_messages(io)

            # make the planchette jump to indicate messages are ready to display
            spirit_board.slide_planchette(SpiritBoard.LOCATIONS["home"],
                                          delay=0.02, step_size=6)
