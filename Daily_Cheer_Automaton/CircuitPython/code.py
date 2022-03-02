# SPDX-FileCopyrightText: 2020 Andy Doro for Adafruit Industries
#
# SPDX-License-Identifier: MIT

# AUTOCHEER DEVICE
# code by Andy Doro
#
# plays an MP3 at a specific time.
#
# uses native CircuitPython mp3 playback
#
# REQUIREMENTS:
# should use M4 (or higher)
# use CircuitPython 5.3.0+
#
#
# HARDWARE:
# Feather M4 Express https://www.adafruit.com/product/3857
# Adalogger https://www.adafruit.com/product/2922
#
#
# TO DO
# ---
# - daylight saving time
# - use built-in NeoPixel as indicator
#

import os
import time
import board
import audiomp3
import audioio
import digitalio


# For hardware I2C (M0 boards) use this line:
import busio as io

# Or for software I2C (ESP8266) use this line instead:
# import bitbangio as io

#import adafruit_ds3231
import adafruit_pcf8523

# SD card
import adafruit_sdcard
import storage

# NeoPixel
#import neopixel


# Use any pin that is not taken by SPI
# For Adalogger FeatherWing: https://learn.adafruit.com/adafruit-adalogger-featherwing/pinouts
# The SDCS pin is the chip select line:
#    On ESP8266, the SD CS pin is on GPIO 15
#    On ESP32 it's GPIO 33
#    On WICED it's GPIO PB5
#    On the nRF52832 it's GPIO 11
#    On Atmel M0, M4, 328p or 32u4 it's on GPIO 10
#    On Teensy 3.x it's on GPIO 10

SD_CS = board.D10 # for M4

# Connect to the card and mount the filesystem.
spi = io.SPI(board.SCK, board.MOSI, board.MISO)
cs = digitalio.DigitalInOut(SD_CS)
sdcard = adafruit_sdcard.SDCard(spi, cs)
vfs = storage.VfsFat(sdcard)
storage.mount(vfs, "/sd")


# Use the filesystem as normal! Our files are under /sd
# This helper function will print the contents of the SD

def print_directory(path, tabs=0):
    for file in os.listdir(path):
        stats = os.stat(path + "/" + file)
        filesize = stats[6]
        isdir = stats[0] & 0x4000

        if filesize < 1000:
            sizestr = str(filesize) + " by"
        elif filesize < 1000000:
            sizestr = "%0.1f KB" % (filesize / 1000)
        else:
            sizestr = "%0.1f MB" % (filesize / 1000000)

        prettyprintname = ""
        for _ in range(tabs):
            prettyprintname += "   "
        prettyprintname += file
        if isdir:
            prettyprintname += "/"
        print('{0:<40} Size: {1:>10}'.format(prettyprintname, sizestr))

        # recursively print directory contents
        if isdir:
            print_directory(path + "/" + file, tabs + 1)


print("Files on filesystem:")
print("====================")
print_directory("/sd")


data = open("/sd/cheer.mp3", "rb")
mp3 = audiomp3.MP3Decoder(data)
#a = audioio.AudioOut(board.A0) # mono
a = audioio.AudioOut(board.A0, right_channel=board.A1) # stereo sound through A0 & A1


i2c = io.I2C(board.SCL, board.SDA)  # Change to the appropriate I2C clock & data
# pins here!

# Create the RTC instance:
#rtc = adafruit_ds3231.DS3231(i2c)
rtc = adafruit_pcf8523.PCF8523(i2c)

# Lookup table for names of days (nicer printing).
days = ("Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday")


# selected time
# 24 hour time
playhour = 19
playmin = 0

# pylint: disable-msg=bad-whitespace
# pylint: disable-msg=using-constant-test
# no DST adjustment yet!
if False:  # change to True if you want to set the time!
    #                     year, mon, date, hour, min, sec, wday, yday, isdst
    t = time.struct_time((2020, 5, 13, 15, 15, 15, 0, -1, -1))
    # you must set year, mon, date, hour, min, sec and weekday
    # yearday is not supported, isdst can be set but we don't do anything with it at this time
    print("Setting time to:", t)  # uncomment for debugging
    rtc.datetime = t
    print()
# pylint: enable-msg=using-constant-test
# pylint: enable-msg=bad-whitespace

# setup NeoPixel
#pixel = neopixel.NeoPixel(board.NEOPIXEL, 1)


# Main loop:
while True:
    t = rtc.datetime

    # print(t)     # uncomment for debugging
    print(
        "The date is {} {}/{}/{}".format(
            days[int(t.tm_wday)], t.tm_mday, t.tm_mon, t.tm_year
        )
    )
    print("The time is {}:{:02}:{:02}".format(t.tm_hour, t.tm_min, t.tm_sec))

    if t.tm_hour == playhour and t.tm_min == playmin:
        print("it is time!")
        # turn NeoPixel green
        #pixel[0] = (0, 255, 0)
        # play the file
        print("playing")
        a.play(mp3)
        while a.playing:
            pass
        print("stopped")
        # turn NeoPixel off
        #pixel[0] = (0, 0, 0)

    time.sleep(1)  # wait a second
