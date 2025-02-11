# SPDX-FileCopyrightText: 2025 Tim Cocks
#
# SPDX-License-Identifier: MIT
"""
Cartoon Character Clock

This project features an analog clock face rendered on a round display.
The art and songs are inspired by an early 20th-century public domain
cartoon.

"""
import os
import time
import board
from adafruit_display_analogclock import AnalogClock
from adafruit_gc9a01a import GC9A01A
import rtc
import socketpool
import displayio
from fourwire import FourWire
import adafruit_ntp
import wifi
import audiobusio
from audiomp3 import MP3Decoder

# Set the desired offset from UTC time here.
# US Eastern Standard Time is -5
# US Eastern Daylight Time is -4
UTC_OFFSET = -5

# enable or disable the hourly chime jingle
HOURLY_CHIME = True

# Set to a tuple containing hour and minute values to
# enable the alarm e.g. 13, 25 will play the alarm at
# 1:25 pm adjusted for the given UTC_OFFSET.
ALARM_TIME = None
#ALARM_TIME = (13, 25)

# WiFi Setup
# Get wifi AP credentials from a settings.toml file
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

# pylint: disable=unsubscriptable-object

if HOURLY_CHIME or ALARM_TIME is not None:
    # Audio Setup
    audio = audiobusio.I2SOut(board.A2, board.A1, board.A0)
    songs = ["song_1.mp3", "song_2.mp3"]
    mp3 = open(songs[0], "rb")
    decoder = MP3Decoder(mp3)

# Display Setup
spi = board.SPI()
tft_cs = board.TX
tft_dc = board.RX

displayio.release_displays()
display_bus = FourWire(spi, command=tft_dc, chip_select=tft_cs, reset=None)
display = GC9A01A(display_bus, width=240, height=240)
display.rotation = 90

# Sync time from NTP server
pool = socketpool.SocketPool(wifi.radio)
ntp = adafruit_ntp.NTP(pool, server="time.nist.gov", tz_offset=0, cache_seconds=3600)
rtc.RTC().datetime = ntp.datetime

# Initialize the clock face
clockface = AnalogClock(
    "clock_short_hand.bmp",
    "clock_long_hand.bmp",
    (120, 120), 106, number_label_scale=2,
    background_color=0x989a97,
    background_img_file="clock_center.bmp",
    background_img_anchor_point=(0.5,0.5),
    background_img_anchored_position=(display.width//2, display.height//2 - 2)
)

# set the clockface to show on the display
display.root_group = clockface

print(f"current time {time.localtime().tm_hour + UTC_OFFSET}:{time.localtime().tm_min}")
cur_hour = time.localtime().tm_hour + UTC_OFFSET
cur_minute = time.localtime().tm_min

clockface.set_time(cur_hour, cur_minute)

while True:
    # If we need to update the clock hands
    if cur_hour != time.localtime().tm_hour + UTC_OFFSET or cur_minute != time.localtime().tm_min:
        # store current values to comapre with next iteration
        cur_hour = time.localtime().tm_hour + UTC_OFFSET
        cur_minute = time.localtime().tm_min

        # update the clock face
        clockface.set_time(cur_hour, cur_minute)

        # if the hourly chime is enabled, and it's the top of the hour
        if HOURLY_CHIME and cur_minute == 0:
            # play the hour chime jingle
            audio.play(decoder)
            while audio.playing:
                pass

        # if the alarm is enabled and the current time is what
        # it was set to.
        if ALARM_TIME is not None and \
                cur_hour == ALARM_TIME[0] and cur_minute == ALARM_TIME[1]:

            # open the alarm song file
            decoder.file = open("song_2.mp3", "rb")

            # play the alarm song twice
            for i in range(2):
                audio.play(decoder)
                while audio.playing:
                    pass
                time.sleep(0.5)

            # re-open the hourly chime file
            decoder.file = open("song_1.mp3", "rb")

    time.sleep(3)
