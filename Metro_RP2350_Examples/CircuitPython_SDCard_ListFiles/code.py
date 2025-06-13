# SPDX-FileCopyrightText: 2021 ladyada for Adafruit Industries
# SPDX-License-Identifier: MIT

"""
CircuitPython Essentials SD Card Read Demo
"""

import os
import digitalio
import busio
import board
import storage
import adafruit_sdcard

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


# This helper function will print the contents of the SD
def print_directory(path, tabs=0):
    for file in os.listdir(path):
        stats = os.stat(path + "/" + file)
        filesize = stats[6]
        isdir = stats[0] & 0x4000

        if filesize < 1000:
            sizestr = str(filesize) + " bytes"
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
        print("{0:<40} Size: {1:>10}".format(prettyprintname, sizestr))

        # recursively print directory contents
        if isdir:
            print_directory(path + "/" + file, tabs + 1)


print("Files on filesystem:")
print("====================")
print_directory("/sd")
