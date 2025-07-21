# SPDX-FileCopyrightText: 2017 Limor Fried for Adafruit Industries
#
# SPDX-License-Identifier: MIT

"""
CircuitPython Essentials SD Card Write Demo
"""

import time
import adafruit_sdcard
import board
import busio
import digitalio
import microcontroller
import storage

# The SD_CS pin is the chip select line.
SD_CS = board.SD_CS


# For CircuitPython 9.x we must initialize and mount the SD card manually.
# On CircuitPython 10.x the core will automatically initialize and mount the SD.
# This try/except block can be removed with 10.x has a stable release.
try:
    # Initialize the Chip Select pin for the SD card
    cs = digitalio.DigitalInOut(SD_CS)
    # Initialize the SD card
    sdcard = adafruit_sdcard.SDCard(
        busio.SPI(board.SD_SCK, board.SD_MOSI, board.SD_MISO), cs
    )
    # Mount the SD card
    vfs = storage.VfsFat(sdcard)
    storage.mount(vfs, "/sd")
except ValueError:
    # "ValueError SD_CS in use" error happen on CircuitPython 10.x
    # because the core initialized the SD automatically. The error
    # can be ignored on 10.x.
    pass

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
