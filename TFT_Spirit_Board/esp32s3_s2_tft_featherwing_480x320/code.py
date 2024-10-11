# SPDX-FileCopyrightText: 2024 Tim Cocks
#
# SPDX-License-Identifier: MIT
"""
SpiritBoard code.py
Feather ESP32-S3 or S2 + TFT Featherwing 3.5" 480x320 pixels

Receive and display messages from the spirits.
"""
import os
import displayio
import board
from digitalio import DigitalInOut
import adafruit_connection_manager
import wifi
import adafruit_requests
from adafruit_io.adafruit_io import IO_HTTP, AdafruitIO_RequestError
from adafruit_hx8357 import HX8357  # TFT Featherwing 3.5" 480x320 display driver
from spirit_board import SpiritBoard
import adafruit_tsc2007


# 3.5" TFT Featherwing is 480x320
displayio.release_displays()
DISPLAY_WIDTH = 480
DISPLAY_HEIGHT = 320

# Initialize TFT Display
spi = board.SPI()
tft_cs = board.D9
tft_dc = board.D10
display_bus = displayio.FourWire(spi, command=tft_dc, chip_select=tft_cs)
display = HX8357(display_bus, width=DISPLAY_WIDTH, height=DISPLAY_HEIGHT)
display.rotation = 0
_touch_flip = (False, True)

# Initialize 3.5" TFT Featherwing Touchscreen
ts_cs_pin = DigitalInOut(board.D6)
i2c = board.I2C()
irq_dio = None
tsc = adafruit_tsc2007.TSC2007(i2c, irq=irq_dio)

# Initialize a requests session
pool = adafruit_connection_manager.get_radio_socketpool(wifi.radio)
ssl_context = adafruit_connection_manager.get_radio_ssl_context(wifi.radio)
requests = adafruit_requests.Session(pool, ssl_context)

# Set your Adafruit IO Username and Key in secrets.py
# (visit io.adafruit.com if you need to create an account,
# or if you need your Adafruit IO key.)
aio_username = os.getenv("AIO_USERNAME")
aio_key = os.getenv("AIO_KEY")

# Initialize an Adafruit IO HTTP API object
io = IO_HTTP(aio_username, aio_key, requests)

# initialize the SpiritBoard class
spirit_board = SpiritBoard(display)

# get messages from io or the local file
messages = spirit_board.get_messages(io)

# The planchette is already at the home position.
# Slide it to home again to make it jump, in order
# indicate the message is ready to be received.
spirit_board.slide_planchette(SpiritBoard.LOCATIONS["home"],
                              delay=0.02, step_size=6)

# current message index
message_index = 0
while True:
    # if the display was touched
    if tsc.touched:
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
