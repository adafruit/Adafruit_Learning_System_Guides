# SPDX-FileCopyrightText: 2018 Jerry Needell for Adafruit Industries
#
# SPDX-License-Identifier: MIT

import sys

import adafruit_sdcard
import board
import busio
import digitalio
import storage

# Connect to the card and mount the filesystem.
spi = busio.SPI(board.SCK, board.MOSI, board.MISO)
cs = digitalio.DigitalInOut(board.SD_CS)
sdcard = adafruit_sdcard.SDCard(spi, cs)
vfs = storage.VfsFat(sdcard)
storage.mount(vfs, "/sd")
sys.path.append("/sd")
