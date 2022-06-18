# SPDX-FileCopyrightText: 2022 Alec Delaney for Adafruit Industries
#
# SPDX-License-Identifier: MIT

import time
import random
import board
import busio
from digitalio import DigitalInOut
import storage
import adafruit_sdcard
import adafruit_logging as logging

# Get chip select pin depending on the board, this one is for the Feather M4 Express
sd_cs = board.D10

# Set up an SD card to write to
spi = busio.SPI(board.SCK, board.MOSI, board.MISO)
cs = DigitalInOut(sd_cs)
sdcard = adafruit_sdcard.SDCard(spi, cs)
vfs = storage.VfsFat(sdcard)
storage.mount(vfs, "/sd")

l = logging.getLogger('file')
l.addHandler(logging.FileHandler('/sd/test.txt'))

def go():
    while True:
        t = random.randint(1, 5)
        if t == 1:
            print('debug')
            l.debug("debug message: %d", random.randint(0, 1000))
        elif t == 2:
            print('info')
            l.info("info message: %d", random.randint(0, 1000))
        elif t == 3:
            print('warning')
            l.warning("warning message: %d", random.randint(0, 1000))
        elif t == 4:
            print('error')
            l.error("error message: %d", random.randint(0, 1000))
        elif t == 5:
            print('critical')
            l.critical("critical message: %d", random.randint(0, 1000))
        time.sleep(5.0 + (random.random() * 5.0))
