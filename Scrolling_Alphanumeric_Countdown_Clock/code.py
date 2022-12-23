# SPDX-FileCopyrightText: 2022 Liz Clark for Adafruit Industries
# SPDX-License-Identifier: MIT
"""
CircuitPython Quad-Alphanumeric Display Holiday Countdown.

This demo requires a separate file named settings.toml on your CIRCUITPY drive, which
should contain your WiFi credentials and Adafruit IO credentials.
"""

import os
import time
import ssl
import wifi
import socketpool
import microcontroller
import board
import adafruit_requests
from adafruit_ht16k33.segments import Seg14x4
from adafruit_io.adafruit_io import IO_HTTP, AdafruitIO_RequestError # pylint: disable=unused-import

# Date and time of event. Update YEAR, MONTH, DAY, HOUR, MINUTE to match the date and time of the
# event to which you are counting down. Update NAME to the name of the event. Update MSG to the
# message you'd like to display when the countdown has completed and the event has started.
EVENT_YEAR = 2022
EVENT_MONTH = 12
EVENT_DAY = 25
EVENT_HOUR = 0
EVENT_MINUTE = 0
EVENT_NAME = "Christmas"
EVENT_MSG = "Merry Christmas * "

# The speed of the text scrolling on the displays. Increase this to slow down the scrolling.
# Decrease it to speed up the scrolling.
scroll_speed = 0.25

# Create the I2C object using STEMMA_I2C()
i2c = board.STEMMA_I2C()
# Alphanumeric segment display setup using three displays in series.
display = Seg14x4(i2c, address=(0x70, 0x71, 0x72))
# Display brightness is a number between 0.0 (off) and 1.0 (maximum). Update this if you want
# to alter the brightness of the characters on the displays.
display.brightness = 0.2
# The setup-successful message. If this shows up on your displays, you have wired them up
# properly and the code setup is correct.
display.print("HELLO WORLD")


def reset_on_error(delay, error):
    """Resets the code after a specified delay, when encountering an error."""
    print("Error:\n", str(error))
    display.print("Error :(")
    print("Resetting microcontroller in %d seconds" % delay)
    time.sleep(delay)
    microcontroller.reset()


try:
    wifi.radio.connect(os.getenv("WIFI_SSID"), os.getenv("WIFI_PASSWORD"))
# any errors, reset MCU
except Exception as e:  # pylint: disable=broad-except
    reset_on_error(10, e)

aio_username = os.getenv("aio_username")
aio_key = os.getenv("aio_key")
location = os.getenv("aio_location")

pool = socketpool.SocketPool(wifi.radio)
requests = adafruit_requests.Session(pool, ssl.create_default_context())
# Initialize an Adafruit IO HTTP API object
try:
    io = IO_HTTP(aio_username, aio_key, requests)
except Exception as e:  # pylint: disable=broad-except
    reset_on_error(10, e)
print("Connected to Adafruit IO")
display.print("Connected IO")

clock = time.monotonic()

event_time = time.struct_time(
    (EVENT_YEAR, EVENT_MONTH, EVENT_DAY, EVENT_HOUR, EVENT_MINUTE, 0, -1, -1, False)
)
scroll_time = 0

while True:
    try:
        if (clock + scroll_time) < time.monotonic():
            now = io.receive_time()
            # print(now)
            # print(event_time)
            remaining = time.mktime(event_time) - time.mktime(now)
            # if it's the day of the event...
            if remaining < 0:
                # scroll the event message on a loop
                display.marquee(EVENT_MSG, scroll_speed, loop=True)
            # calculate the seconds remaining
            secs_remaining = remaining % 60
            remaining //= 60
            # calculate the minutes remaining
            mins_remaining = remaining % 60
            remaining //= 60
            # calculate the hours remaining
            hours_remaining = remaining % 24
            remaining //= 24
            # calculate the days remaining
            days_remaining = remaining
            # pack the calculated times into a string to scroll
            countdown_string = (
                "* %d Days, %d Hours, %d Minutes & %s Seconds until %s *"
                % (
                    days_remaining,
                    hours_remaining,
                    mins_remaining,
                    secs_remaining,
                    EVENT_NAME,
                )
            )
            # get the length of the packed string
            display_length = len(countdown_string)
            # print(display_length)
            # calculate the amount of time needed to scroll the string
            scroll_time = display_length * scroll_speed
            # print(scroll_time)
            # reset the clock
            clock = time.monotonic()
            # scroll the string once
            display.marquee(countdown_string, scroll_speed, loop=False)

    # any errors, reset MCU
    except Exception as e:  # pylint: disable=broad-except
        reset_on_error(10, e)
