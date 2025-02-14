# SPDX-FileCopyrightText: Copyright (c) 2024 Liz Clark for Adafruit Industries
#
# SPDX-License-Identifier: MIT

import csv
import os
import sys
import board
import busio
from digitalio import DigitalInOut
from adafruit_pn532.spi import PN532_SPI

spi = busio.SPI(board.SCK, board.MOSI, board.MISO)
cs_pin = DigitalInOut(board.D24)
pn532 = PN532_SPI(spi, cs_pin, debug=False)

csv_file = "movies.csv"
if not os.path.isfile(csv_file):
    with open(csv_file, mode='w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(['uid', 'movie'])

def is_duplicate(uid, mov):
    with open(csv_file, mode='r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row['uid'] == uid or row['movie'] == mov:
                return True
    return False

ic, ver, rev, support = pn532.firmware_version
print("Found PN532 with firmware version: {0}.{1}".format(ver, rev))

# Configure PN532 to communicate with MiFare cards
pn532.SAM_configuration()

print("Waiting for new RFID/NFC card...")

while True:
    the_uid = pn532.read_passive_target(timeout=0.05)
    if the_uid is not None:
        uid_str = f"{[hex(i) for i in the_uid]}"
        movie = input("Enter the name of the new movie: ")
        movie = f"{movie}"
        if is_duplicate(uid_str, movie):
            print("UID {uid_str} or movie {movie} already exists, skipping.")
        else:
            with open(csv_file, mode='a', newline='') as file:
                writer = csv.writer(file)
                writer.writerow([uid_str, movie])
            print(f"Added UID {uid_str} with movie title {movie} to movies.csv")
            sys.exit()
