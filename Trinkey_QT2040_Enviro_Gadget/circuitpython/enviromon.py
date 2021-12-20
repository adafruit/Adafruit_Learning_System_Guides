# SPDX-FileCopyrightText: 2021 Carter Nelson for Adafruit Industries
#
# SPDX-License-Identifier: MIT

import time
import board
import usb_cdc
import adafruit_scd4x
from adafruit_bme280 import basic as adafruit_bme280
import neopixel

#--| User Config |-----------------------------------
DATA_FORMAT = "JSON"    # data format, CSV or JSON
DATA_RATE = 5           # data read rate in secs
BEAT_COLOR = 0xADAF00   # neopixel heart beat color
BEAT_RATE = 1           # neopixel heart beat rate in secs, 0=none
#----------------------------------------------------

# check that USB CDC data has been enabled
if usb_cdc.data is None:
    print("Need to enable USB CDC serial data in boot.py.")
    while True:
        pass

# setup stuff
scd = adafruit_scd4x.SCD4X(board.I2C())
scd.start_periodic_measurement()
bme = adafruit_bme280.Adafruit_BME280_I2C(board.I2C())
pixel = neopixel.NeoPixel(board.NEOPIXEL, 1)

# CSV output
def send_csv_data(values):
    usb_cdc.data.write("{}, {}, {}, {}\n".format(*values).encode())

# JSON output
def send_json_data(values):
    usb_cdc.data.write('{'.encode())
    usb_cdc.data.write('"CO2" : {},'.format(values[0]).encode())
    usb_cdc.data.write('"pressure" : {},'.format(values[1]).encode())
    usb_cdc.data.write('"temperature" : {},'.format(values[2]).encode())
    usb_cdc.data.write('"humidity" : {}'.format(values[3]).encode())
    usb_cdc.data.write('}\n'.encode())

# init time tracking
last_data = last_beat = time.monotonic()

# loop forever!
while True:
    current_time = time.monotonic()

    # data
    if current_time - last_data > DATA_RATE:
        data = (scd.CO2, bme.pressure, bme.temperature, bme.humidity)
        usb_cdc.data.reset_output_buffer()
        if DATA_FORMAT == "CSV":
            send_csv_data(data)
        elif DATA_FORMAT == "JSON":
            send_json_data(data)
        else:
            usb_cdc.data.write(b"Unknown data format.\n")
        last_data = current_time

    # heart beat
    if BEAT_RATE and current_time - last_beat > BEAT_RATE:
        if pixel[0][0]:
            pixel.fill(0)
        else:
            pixel.fill(BEAT_COLOR)
        last_beat = current_time
