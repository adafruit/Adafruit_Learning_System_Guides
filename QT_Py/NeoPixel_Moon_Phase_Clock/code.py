# SPDX-FileCopyrightText: 2025 Liz Clark for Adafruit Industries
# SPDX-License-Identifier: MIT

import os
import time
import ssl
import board
import wifi
import socketpool
import microcontroller
import neopixel
import adafruit_requests
from adafruit_ticks import ticks_ms, ticks_add, ticks_diff

# US Navy Astronomical Applications API for moon phase
# https://aa.usno.navy.mil/api
# Your location coordinates (adjust these to your location)
LATITUDE = 40.71
LONGITUDE = -74.0060
TIMEZONE = -5  # EST/EDT, adjust for your timezone
DST = True  # Set to False if not in daylight saving time

# Adafruit IO time server for current date, no API key needed
date_url = "https://io.adafruit.com/api/v2/time/ISO-8601"
# connect to wifi
try:
    wifi.radio.connect(os.getenv('CIRCUITPY_WIFI_SSID'), os.getenv('CIRCUITPY_WIFI_PASSWORD'))
except TypeError:
    print("Could not find WiFi info. Check your settings.toml file!")
    raise
pool = socketpool.SocketPool(wifi.radio)
requests = adafruit_requests.Session(pool, ssl.create_default_context())

# neopixels, 49 total
OFF = (0, 0, 0)
ON = (255, 255, 255)
RED = (255,0,0)
pixel_pin = board.A3
num_pixels = 49
pixels = neopixel.NeoPixel(pixel_pin, num_pixels, brightness=0.1, auto_write=False)
pixels.fill(0)

# phases of the moon
NEW_MOON = 0
WAXING_CRESCENT = 1
FIRST_QUARTER = 2
WAXING_GIBBOUS = 3
FULL_MOON = 4
WANING_GIBBOUS = 5
LAST_QUARTER = 6
WANING_CRESCENT = 7
DARK_MOON = 8
RED_MOON = 9
# strings that match return from API
phase_names = ["New Moon", "Waxing Crescent", "First Quarter", "Waxing Gibbous",
          "Full Moon", "Waning Gibbous", "Last Quarter", "Waning Crescent","Dark Moon","Red Moon"]

# functions for each moon phase to light up based on neopixel orientation
def set_new_moon():
    pixels.fill(OFF)
    pixels.show()

def set_waxing_crescent():
    pixels.fill(OFF)
    for i in range(31, 44):
        pixels[i] = ON
    pixels.show()

def set_first_quarter():
    pixels.fill(OFF)
    for i in range(24, 49):
        pixels[i] = ON
    pixels.show()

def set_waxing_gibbous():
    pixels.fill(OFF)
    for i in range(0, 4):
        pixels[i] = ON
    for i in range(18, 49):
        pixels[i] = ON
    pixels.show()

def set_full_moon():
    pixels.fill(ON)
    pixels.show()

def set_waning_gibbous():
    pixels.fill(OFF)
    for i in range(0, 30):
        pixels[i] = ON
    for i in range(44, 49):
        pixels[i] = ON
    pixels.show()

def set_last_quarter():
    pixels.fill(OFF)
    for i in range(0, 24):
        pixels[i] = ON
    pixels.show()

def set_waning_crescent():
    pixels.fill(OFF)
    for i in range(5, 18):
        pixels[i] = ON
    pixels.show()

def set_dark_moon():
    pixels.fill(OFF)
    for i in range(9,14):
        pixels[i] = ON
    pixels.show()

def set_red_moon():
    pixels.fill(RED)
    pixels.show()

# match functions with phases
phase_functions = {
    NEW_MOON: set_new_moon,
    WAXING_CRESCENT: set_waxing_crescent,
    FIRST_QUARTER: set_first_quarter,
    WAXING_GIBBOUS: set_waxing_gibbous,
    FULL_MOON: set_full_moon,
    WANING_GIBBOUS: set_waning_gibbous,
    LAST_QUARTER: set_last_quarter,
    WANING_CRESCENT: set_waning_crescent,
    DARK_MOON: set_dark_moon,
    RED_MOON: set_red_moon
}

# test function, runs through all 8 in order
def demo_all_phases(delay=1):
    for phase in range(9):
        print(f"Setting phase: {phase_names[phase]}")
        phase_functions[phase]()
        time.sleep(delay)
demo_all_phases()

# takes response from API, matches to function, runs function
def set_moon_phase(phase):
    phase_lower = phase.lower()
    error_check = 0
    for i, name in enumerate(phase_names):
        if phase_lower == name.lower():
            error_check = 1
            phase_functions[i]()
            print(f"Moon phase set to: {name}")
    if error_check == 0:
        print("ERROR")
        set_red_moon() #error indicator if API responce is unexpected

# time keeping, fetches API every 6 hours
timer_clock = ticks_ms()
timer = (6 * 3600) * 1000
first_run = True

while True:
    try:
        if first_run or ticks_diff(ticks_ms(), timer_clock) >= timer:
			# get current date
            date_response = requests.get(date_url)
            iso_date = date_response.text.strip('"')
            current_date = iso_date.split('T')[0]
            date_response.close()
			# build Navy API URL with parameters
            # pylint: disable=line-too-long
            url = f"https://aa.usno.navy.mil/api/rstt/oneday?date={current_date}&coords={LATITUDE},{LONGITUDE}&tz={TIMEZONE}"
            if DST:
                url += "&dst=true"
			# get the JSON response
            response = requests.get(url)
            json_response = response.json()
			# isolate phase info
            current_phase = json_response["properties"]["data"]["curphase"]
            print("-" * 40)
            print(current_phase)
            print("-" * 40)
			# run function to update neopixels with current phase
            set_moon_phase(current_phase)
            response.close()
            time.sleep(1)
            first_run = False
			# reset clock
            timer_clock = ticks_add(timer_clock, timer)
    # pylint: disable=broad-except
    except Exception as e:
        print("Error:\n", str(e))
        print("Resetting microcontroller in 10 seconds")
        time.sleep(10)
        microcontroller.reset()
