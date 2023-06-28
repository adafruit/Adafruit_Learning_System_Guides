# SPDX-FileCopyrightText: 2023 Liz Clark for Adafruit Industries
#
# SPDX-License-Identifier: MIT

import os
import ssl
import time
import wifi
import socketpool
import board
import busio
import microcontroller
import adafruit_requests
import neopixel
from adafruit_ticks import ticks_ms, ticks_add, ticks_diff
from adafruit_io.adafruit_io import IO_HTTP, AdafruitIO_RequestError

pixel_pin = board.NEOPIXEL
num_pixels = 1

pixels = neopixel.NeoPixel(pixel_pin, num_pixels, brightness=0.05, auto_write=False)
pixels.fill((255, 255, 0))
pixels.show()

try:
    wifi.radio.connect(os.getenv('CIRCUITPY_WIFI_SSID'), os.getenv('CIRCUITPY_WIFI_PASSWORD'))
except Exception as e: # pylint: disable=broad-except
    pixels.fill((100, 100, 100))
    pixels.show()
    print("Error:\n", str(e))
    print("Resetting microcontroller in 5 seconds")
    time.sleep(5)
    microcontroller.reset()

aio_username = os.getenv('aio_username')
aio_key = os.getenv('aio_key')

try:
    pool = socketpool.SocketPool(wifi.radio)
    requests = adafruit_requests.Session(pool, ssl.create_default_context())
    # Initialize an Adafruit IO HTTP API object
    io = IO_HTTP(aio_username, aio_key, requests)
    print("connected to io")
except Exception as e: # pylint: disable=broad-except
    pixels.fill((100, 100, 100))
    pixels.show()
    print("Error:\n", str(e))
    print("Resetting microcontroller in 5 seconds")
    time.sleep(5)
    microcontroller.reset()

try:
# get feed
    ikea_pm25 = io.get_feed("ikeapm25")
except AdafruitIO_RequestError:
# if no feed exists, create one
    ikea_pm25 = io.create_new_feed("ikeapm25")

uart = busio.UART(board.TX, board.RX, baudrate=9600)

measurements = [0, 0, 0, 0, 0]
measurement_idx = 0

def valid_header(d):
    headerValid = (d[0] == 0x16 and d[1] == 0x11 and d[2] == 0x0B)
    # debug
    # if not headerValid:
        # print("msg without header")
    return headerValid

start_read = False
clock = ticks_ms()
pixels.fill((0, 255, 0))
pixels.show()

io_time = 60000

while True:
    try:
        data = uart.read(32)  # read up to 32 bytes
        #print(data)  # this is a bytearray type
        time.sleep(0.01)
        if ticks_diff(ticks_ms(), clock) >= io_time:
            pixels.fill((0, 0, 255))
            pixels.show()
            io_data = measurements[0]
            if io_data != 0:
                io.send_data(ikea_pm25["key"], io_data)
                print(f"sent {io_data} to {ikea_pm25['key']} feed")
            time.sleep(1)
            clock = ticks_add(clock, io_time)
            pixels.fill((0, 0, 0))
            pixels.show()
        if data is not None:
            v = valid_header(data)
            if v is True:
                measurement_idx = 0
                start_read = True
            if start_read is True:
                pixels.fill((255, 0, 0))
                pixels.show()
                pm25 = (data[5] << 8) | data[6]
                measurements[measurement_idx] = pm25
                if measurement_idx == 4:
                    start_read = False
                measurement_idx = (measurement_idx + 1) % 5
                print(pm25)
                print(measurements)
        else:
            pixels.fill((0, 255, 0))
            pixels.show()
    except Exception as e: # pylint: disable=broad-except
        print("Error:\n", str(e))
        print("Resetting microcontroller in 5 seconds")
        time.sleep(5)
        microcontroller.reset()
