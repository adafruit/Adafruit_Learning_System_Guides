# SPDX-FileCopyrightText: 2023 Liz Clark for Adafruit Industries
#
# SPDX-License-Identifier: MIT
"""CircuitPython PiCowbell Adalogger Example"""
import time
import board
import sdcardio
import busio
import storage
import adafruit_mcp9808
from adafruit_pcf8523.pcf8523 import PCF8523

#  setup for Pico I2C
i2c = busio.I2C(board.GP5, board.GP4)
# setup for mcp9808 temp monitor
mcp9808 = adafruit_mcp9808.MCP9808(i2c)
# setup for RTC
rtc = PCF8523(i2c)

#  list of days to print to the text file on boot
days = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday")

# SPI SD_CS pin
SD_CS = board.GP17

#  SPI setup for SD card
spi = busio.SPI(board.GP18, board.GP19, board.GP16)
sdcard = sdcardio.SDCard(spi, SD_CS)
vfs = storage.VfsFat(sdcard)
try:
    storage.mount(vfs, "/sd")
    print("sd card mounted")
except ValueError:
    print("no SD card")

#  to update the RTC, change set_clock to True
#  otherwise RTC will remain set
#  it should only be needed after the initial set
#  if you've removed the coincell battery
set_clock = False

if set_clock:
    #                     year, mon, date, hour, min, sec, wday, yday, isdst
    t = time.struct_time((2023,  3,   6,   00,  00,  00,    0,   -1,    -1))

    print("Setting time to:", t)
    rtc.datetime = t
    print()

#  variable to hold RTC datetime
t = rtc.datetime

time.sleep(1)

def get_temp(sensor):
    temperature_celsius = sensor
    temperature_fahrenheit = temperature_celsius * 9 / 5 + 32
    return temperature_fahrenheit

#  initial write to the SD card on startup
try:
    with open("/sd/temp.txt", "a") as f:
        #  writes the date
        f.write('The date is {} {}/{}/{}\n'.format(days[t.tm_wday], t.tm_mon, t.tm_mday, t.tm_year))
        #  writes the start time
        f.write('Start time: {}:{}:{}\n'.format(t.tm_hour, t.tm_min, t.tm_sec))
        #  headers for data, comma-delimited
        f.write('Temp,Time\n')
        #  debug statement for REPL
        print("initial write to SD card complete, starting to log")
except ValueError:
    print("initial write to SD card failed - check card")

while True:
    try:
        #  variable for RTC datetime
        t = rtc.datetime
        #  append SD card text file
        with open("/sd/temp.txt", "a") as f:
            #  read temp data from mcp9808
            temp = get_temp(mcp9808.temperature)
            #  write temp data followed by the time, comma-delimited
            f.write('{},{}:{}:{}\n'.format(temp, t.tm_hour, t.tm_min, t.tm_sec))
            print("data written to sd card")
        #  repeat every 30 seconds
        time.sleep(30)
    except ValueError:
        print("data error - cannot write to SD card")
        time.sleep(10)
