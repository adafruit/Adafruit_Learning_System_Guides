# SPDX-FileCopyrightText: 2017 Limor Fried for Adafruit Industries
#
# SPDX-License-Identifier: MIT

"""
CircuitPython Essentials SD Card Write Demo
REMOVE THIS LINE AND ALL BELOW IT BEFORE SUBMITTING TO LEARN
Update CHIP_SELECT_PIN to match the CS pin on your board.

For example, for the Metro ESP32-S3, you would use: board.SD_CS.
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

# Connect to the card and mount the filesystem.
cs = digitalio.DigitalInOut(SD_CS)
sdcard = adafruit_sdcard.SDCard(busio.SPI(board.SD_SCK, board.SD_MOSI, board.SD_MISO), cs)
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
