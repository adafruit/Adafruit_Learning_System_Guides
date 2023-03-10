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
import simpleio
from adafruit_ticks import ticks_ms, ticks_add, ticks_diff
from adafruit_io.adafruit_io import IO_HTTP

# latitude
lat = 42.36
# longitude
long = -71.06

# neopixel setup
NUMPIXELS = 30  # number of neopixels
BRIGHTNESS = 0.5  # A number between 0.0 and 1.0, where 0.0 is off, and 1.0 is max.
PIN = board.A3  # This is the default pin on the NeoPixel Driver BFF.

pixels = neopixel.NeoPixel(PIN, NUMPIXELS, brightness=BRIGHTNESS, auto_write=False)

# turn on NeoPixels on boot to check wiring
pixels.fill((255, 125, 0))
pixels.show()

# API request to open-meteo
weather_url = "https://api.open-meteo.com/v1/forecast?"
# pass latitude and longitude
# will return sunrise and sunset times
weather_url += "latitude=%d&longitude=%d&timezone=auto&daily=sunrise,sunset" % (lat, long)

#  connect to SSID
wifi.radio.connect(os.getenv('CIRCUITPY_WIFI_SSID'), os.getenv('CIRCUITPY_WIFI_PASSWORD'))

pool = socketpool.SocketPool(wifi.radio)
requests = adafruit_requests.Session(pool, ssl.create_default_context())

pool = socketpool.SocketPool(wifi.radio)

# adafruit IO info
aio_username = os.getenv('aio_username')
aio_key = os.getenv('aio_key')
location = "America/New York"

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

# get the time on start-up
# pylint: disable=broad-except
try:
    now = get_request(5, io.receive_time())
except Exception as e:
    reset_on_error(10, e)
print(now)
today = now.tm_mday

# function to make a request to open-meteo
def sun_clock():
    # make the API request
    response = get_request(5, requests.get(weather_url))
    # packs the response into a JSON
    response_as_json = response.json()
    # gets sunrise
    _rise = response_as_json['daily']['sunrise'][0]
    # gets sunset
    _set = response_as_json['daily']['sunset'][0]
    return _rise, _set

# initial API call
try:
    sunrise, sunset = sun_clock()
except Exception as e:
    reset_on_error(10, e)

print(sunrise)
print(sunset)

# the sunrise/sunset time is returned as a JSON aka a string
# this function chops up the string to get the hours and minutes as integers
def divide_time(z):
    string_time = z.split("-")
    clock_time = string_time[2].split("T")
    int_time = clock_time[1].split(":")
    event_time = time.struct_time(
    (int(string_time[0]), int(string_time[1]), int(clock_time[0]), int(int_time[0]),
    int(int_time[1]), 0, -1, -1, False)
    )
    # print(event_time)
    return event_time

rise_time = divide_time(sunrise)
set_time = divide_time(sunset)

# function that tracks how many hours/minutes until sunrise or sunset
def sun_countdown(sun_event):
    n = get_request(5, io.receive_time())
    remaining = time.mktime(sun_event) - time.mktime(n)
    r = remaining
    # print(remaining)
    # calculate the seconds remaining
    secs_remaining = remaining % 60 # pylint: disable=unused-variable
    remaining //= 60
    # calculate the minutes remaining
    minutes_until = remaining % 60
    remaining //= 60
    # calculate the hours remaining
    hours_until = remaining % 24
    remaining //= 24
    return r, hours_until, minutes_until, n
try:
    total_until_rise, hours_until_sunrise, mins_until_sunrise, now = sun_countdown(rise_time)
except Exception as e:
    reset_on_error(10, e)
try:
    total_until_set, hours_until_sunset, mins_until_sunset, now = sun_countdown(set_time)
except Exception as e:
    reset_on_error(10, e)

# red and yellow color percentage for neopixels
percent_red = 0
percent_yellow = 0

print(total_until_set)
# check to see if the star fragment should be lit up on start-up
if total_until_set < 0:
    print("star glow true")
    star_glow = True
    percent_red = 255
    percent_yellow = 125
    # turn neopixels on using RGB values
    pixels.fill((percent_red, percent_yellow, 0))
    pixels.show()
else:
    print("star glow false")
    star_glow = False
    percent_red = 0
    percent_yellow = 0
    # turn neopixels on using RGB values
    pixels.fill((percent_red, percent_yellow, 0))
    pixels.show()

# ticks time tracker
clock = ticks_ms()

# tracker for initial start-up state
first_run = True

# 15 minutes in milliseconds
time_check = 900000
# state to tell if it's after midnight yet before sunrise
looking_for_sunrise = False

while True:
    try:
        # if it's daytime
        if not star_glow:
            # every 15 minutes...
            if first_run or ticks_diff(ticks_ms(), clock) > time_check:
                print("pinging Open-Meteo")
                sunrise, sunset = sun_clock()
                (total_until_set, hours_until_sunset,
                mins_until_sunset, now) = sun_countdown(set_time)
                print(now)
                print("%d hour(s) until sunset" % hours_until_sunset)
                print("%d minutes(s) until sunset" % mins_until_sunset)
                print(sunset)
                print(percent_red)
                print()
                # less than an hour until sunset...
                if hours_until_sunset in (0, 23):
                    # check every minute
                    time_check = 300000
                    # map color to ramp up in brightness over the course of the final hour
                    percent_red = simpleio.map_range(mins_until_sunset, 59, 0, 0, 255)
                    percent_yellow = simpleio.map_range(mins_until_sunset, 59, 0, 0, 125)
                    # if the sun has set..
                    if total_until_set < 0:
                        percent_red = 255
                        percent_yellow = 125
                        time_check = 900000
                        star_glow = True
                        print("star is glowing")
                # otherwise just keep checking every 15 minutes
                else:
                    time_check = 900000
                    percent_red = 0
                    percent_yellow = 0
                if first_run:
                    first_run = False
                else:
                    # reset clock
                    clock = ticks_add(clock, time_check)
        # if it's nighttime...
        else:
            if first_run or ticks_diff(ticks_ms(), clock) > time_check:
                if today != now.tm_mday or (first_run and now.tm_hour < rise_time.tm_hour):
                    today = now.tm_mday
                    looking_for_sunrise = True
                # begin tracking the incoming sunrise
                if looking_for_sunrise:
                    print("pinging Open-Meteo")
                    sunrise, sunset = sun_clock()
                    (total_until_rise, hours_until_sunrise,
                    mins_until_sunrise, now) = sun_countdown(rise_time)
                    print(now)
                    print("%d hour(s) until sunrise" % hours_until_sunrise)
                    print("%d minutes(s) until sunrise" % mins_until_sunrise)
                    print(sunrise)
                    print(now)
                    print()
                    # less than an hour until sunset...
                    if hours_until_sunrise in (0, 23):
                        # check every minute
                        time_check = 300000
                        # map color to decrease brightness over the course of the final hour
                        percent_red = simpleio.map_range(mins_until_sunrise, 59, 0, 255, 0)
                        percent_yellow = simpleio.map_range(mins_until_sunrise, 59, 0, 125, 0)
                        # if the sun has risen..
                        if total_until_rise < 0:
                            percent_red = 0
                            percent_yellow = 0
                            time_check = 900000
                            star_glow = False
                            looking_for_sunrise = False
                            print("star is off")
                    # otherwise just keep checking every 15 minutes
                    # and keep neopixels on
                    else:
                        time_check = 900000
                        percent_red = 255
                        percent_yellow = 125
                # otherwise just keep checking every 15 minutes
                # and keep neopixels on
                else:
                    now = get_request(5, io.receive_time())
                    print("not looking for sunrise")
                    print(now)
                    print()
                    time_check = 900000
                    percent_red = 255
                    percent_yellow = 125
                if first_run:
                    first_run = False
                else:
                    # reset clock
                    clock = ticks_add(clock, time_check)
        # turn neopixels on using RGB values
        pixels.fill((percent_red, percent_yellow, 0))
        pixels.show()
    except Exception as e:
        reset_on_error(10, e)
