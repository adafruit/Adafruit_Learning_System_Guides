# SPDX-FileCopyrightText: 2022 Liz Clark for Adafruit Industries
# SPDX-License-Identifier: MIT

import os
import time
import ssl
import wifi
import socketpool
import microcontroller
import board
import busio
import adafruit_requests
import adafruit_ahtx0
from adafruit_io.adafruit_io import IO_HTTP, AdafruitIO_RequestError

wifi.radio.connect(os.getenv('CIRCUITPY_WIFI_SSID'), os.getenv('CIRCUITPY_WIFI_PASSWORD'))

aio_username = os.getenv('aio_username')
aio_key = os.getenv('aio_key')

pool = socketpool.SocketPool(wifi.radio)
requests = adafruit_requests.Session(pool, ssl.create_default_context())
# Initialize an Adafruit IO HTTP API object
io = IO_HTTP(aio_username, aio_key, requests)
print("connected to io")

#  use Pico W's GP0 for SDA and GP1 for SCL
i2c = busio.I2C(board.GP1, board.GP0)
aht20 = adafruit_ahtx0.AHTx0(i2c)

try:
# get feed
    picowTemp_feed = io.get_feed("pitemp")
    picowHumid_feed = io.get_feed("pihumid")
except AdafruitIO_RequestError:
# if no feed exists, create one
    picowTemp_feed = io.create_new_feed("pitemp")
    picowHumid_feed = io.create_new_feed("pihumid")

#  pack feed names into an array for the loop
feed_names = [picowTemp_feed, picowHumid_feed]
print("feeds created")

clock = 300

while True:
    try:
        #  when the clock runs out..
        if clock > 300:
            #  read sensor
            data = [aht20.temperature, aht20.relative_humidity]
            #  send sensor data to respective feeds
            for z in range(2):
                io.send_data(feed_names[z]["key"], data[z])
                print("sent %0.1f" % data[z])
                time.sleep(1)
            #  print sensor data to the REPL
            print("\nTemperature: %0.1f C" % aht20.temperature)
            print("Humidity: %0.1f %%" % aht20.relative_humidity)
            print()
            time.sleep(1)
            #  reset clock
            clock = 0
        else:
            clock += 1
    # pylint: disable=broad-except
    #  any errors, reset Pico W
    except Exception as e:
        print("Error:\n", str(e))
        print("Resetting microcontroller in 10 seconds")
        time.sleep(10)
        microcontroller.reset()
    #  delay
    time.sleep(1)
    print(clock)
