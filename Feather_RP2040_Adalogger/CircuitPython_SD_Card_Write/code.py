# SPDX-FileCopyrightText: 2017 Limor Fried for Adafruit Industries
#
# SPDX-License-Identifier: MIT

"""
CircuitPython Essentials SD Card Write Demo
Feather RP2040 Adalogger
"""

import time
import busio
import board
import digitalio
import microcontroller
import storage
import adafruit_sdcard

# Connect to the card and mount the filesystem.
cs = digitalio.DigitalInOut(board.SD_CS)
sd_spi = busio.SPI(board.SD_CLK, board.SD_MOSI, board.SD_MISO)
sdcard = adafruit_sdcard.SDCard(sd_spi, cs)
vfs = storage.VfsFat(sdcard)
storage.mount(vfs, "/sd")

# Use the filesystem as normal! Our files are under /sd

print("Logging temperature to filesystem")
# append to the file!
while True:
    # open file for append
    with open("/sd/temperature.txt", "a") as f:
        t = microcontroller.cpu.temperature
        print("Temperature = %0.1f" % t)
        f.write("%0.1f\n" % t)
    # file is saved
    time.sleep(1)
