# SPDX-FileCopyrightText: 2021 Liz Clark for Adafruit Industries
#
# SPDX-License-Identifier: MIT

import time
import board
import adafruit_scd4x
import sdcardio
import busio
import storage
import adafruit_pcf8523

#  setup for I2C
i2c = board.I2C()  # uses board.SCL and board.SDA
# i2c = board.STEMMA_I2C()  # For using the built-in STEMMA QT connector on a microcontroller
#  setup for SCD40
scd4x = adafruit_scd4x.SCD4X(i2c)
#  setup for RTC
rtc = adafruit_pcf8523.PCF8523(i2c)
#  start measuring co2 with SCD40
scd4x.start_periodic_measurement()
#  list of days to print to the text file on boot
days = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday")

# SPI SD_CS pin
SD_CS = board.D10

#  SPI setup for SD card
spi = busio.SPI(board.SCK, board.MOSI, board.MISO)
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
    t = time.struct_time((2021,  10,   31,   00,  00,  00,    0,   -1,    -1))

    print("Setting time to:", t)
    rtc.datetime = t
    print()

#  variable to hold RTC datetime
t = rtc.datetime

time.sleep(1)

#  initial write to the SD card on startup
try:
    with open("/sd/co2.txt", "a") as f:
        #  writes the date
        f.write('The date is {} {}/{}/{}\n'.format(days[t.tm_wday], t.tm_mday, t.tm_mon, t.tm_year))
        #  writes the start time
        f.write('Start time: {}:{}:{}\n'.format(t.tm_hour, t.tm_min, t.tm_sec))
        #  headers for data, comma-delimited
        f.write('CO2,Time\n')
        #  debug statement for REPL
        print("initial write to SD card complete, starting to log")
except ValueError:
    print("initial write to SD card failed - check card")

while True:
    try:
        #  variable for RTC datetime
        t = rtc.datetime
        #  append SD card text file
        with open("/sd/co2.txt", "a") as f:
            #  read co2 data from SCD40
            co2 = scd4x.CO2
            #  write co2 data followed by the time, comma-delimited
            f.write('{},{}:{}:{}\n'.format(co2, t.tm_hour, t.tm_min, t.tm_sec))
            print("data written to sd card")
        #  repeat every 30 seconds
        time.sleep(30)
    except ValueError:
        print("data error - cannot write to SD card")
        time.sleep(10)
