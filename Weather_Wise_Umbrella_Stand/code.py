# SPDX-FileCopyrightText: 2023 Liz Clark for Adafruit Industries
# SPDX-License-Identifier: MIT

import os
import ssl
import time
import microcontroller
import board
import wifi
import socketpool
import adafruit_requests
import neopixel
from adafruit_ticks import ticks_ms, ticks_add, ticks_diff
from adafruit_io.adafruit_io import IO_HTTP

# latitude
lat = 38.58
# longitude
long = -121.49
# hours in 24 hour time that the pixels should be off
hours_off = (0, 6)
# color of the pixels when rain is expected
PIXELS_COLOR = (0, 0, 255)

# neopixel setup
NUMPIXELS = 30  # number of neopixels
BRIGHTNESS = 0.5  # A number between 0.0 and 1.0, where 0.0 is off, and 1.0 is max.
PIN = board.GP0

pixels = neopixel.NeoPixel(PIN, NUMPIXELS, brightness=BRIGHTNESS, auto_write=False)

# turn on NeoPixels on boot to check wiring
pixels.fill(PIXELS_COLOR)
pixels.show()

# API request to open-meteo
weather_url = "https://api.open-meteo.com/v1/forecast?"
# pass latitude and longitude
# will return sunrise and sunset times
weather_url += "latitude=%d&longitude=%d&timezone=auto&hourly=rain&forecast_days=1" % (lat, long)

#  connect to SSID
wifi.radio.connect(os.getenv('CIRCUITPY_WIFI_SSID'), os.getenv('CIRCUITPY_WIFI_PASSWORD'))

pool = socketpool.SocketPool(wifi.radio)
requests = adafruit_requests.Session(pool, ssl.create_default_context())

pool = socketpool.SocketPool(wifi.radio)

# adafruit IO info
aio_username = os.getenv('aio_username')
aio_key = os.getenv('aio_key')
location = "America/Los Angeles"

# io HTTP for getting the time from the internet
io = IO_HTTP(aio_username, aio_key, requests)

def reset_on_error(delay, error):
    print("Error:\n", str(error))
    print("Resetting microcontroller in %d seconds" % delay)
    time.sleep(delay)
    microcontroller.reset()

# function for making http requests with try/except
def get_request(tries, ping):
    for i in range(tries):
        try:
            n = ping
        except Exception as error:
            print(error)
            time.sleep(10)
            if i < tries - 1:
                continue
            raise
        break
    return n

# pylint: disable=broad-except
# function to make a request to open-meteo & time from IO
def rain_check():
    # gets current time
    now = get_request(5, io.receive_time())
    h = now.tm_hour
    time.sleep(1)
    # make the API request
    weather_call = get_request(5, requests.get(weather_url))
    # packs the response into a JSON
    response_as_json = weather_call.json()
    # gets rain forecast
    _chance = response_as_json['hourly']['rain']
    return h, _chance

# ticks time tracker
clock = ticks_ms()

# tracker for initial start-up state
first_run = True

# 15 minutes in milliseconds
time_check = 900000

while True:
    try:
        # every 15 minutes...
        if first_run or ticks_diff(ticks_ms(), clock) > time_check:
            print("pinging Open-Meteo")
            hour, rain_chance = rain_check()
            print("Rain expected: %.2f mm" % rain_chance[hour])
            if hour in hours_off:
                print("sleeping, please don't tell me it's raining")
                color = (0, 0, 0)
            else:
                # if rain is expected. turn pixels blue
                if rain_chance[hour] > 0:
                    print("tut tut, looks like rain")
                    color = PIXELS_COLOR
                # otherwise turn pixels off
                else:
                    print("no rain expected")
                    color = (0, 0, 0)
            if first_run:
                first_run = False
            else:
                pixels.fill(color)
                pixels.show()
                # reset clock
                clock = ticks_add(clock, time_check)
    except Exception as e:
        reset_on_error(10, e)
