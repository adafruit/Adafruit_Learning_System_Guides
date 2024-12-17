# SPDX-FileCopyrightText: 2024 Liz Clark for Adafruit Industries
#
# SPDX-License-Identifier: MIT

import time
import os
import ssl
import wifi
import socketpool
import microcontroller
import board
import digitalio
import adafruit_requests
from adafruit_io.adafruit_io import IO_HTTP, AdafruitIO_RequestError

aio_username = os.getenv("ADAFRUIT_AIO_USERNAME")
aio_key = os.getenv("ADAFRUIT_AIO_KEY")

# buttons
button = digitalio.DigitalInOut(board.D5)
button.direction = digitalio.Direction.INPUT
button.pull = digitalio.Pull.UP
button_state = False

lights_on = False

print()
print("Connecting to WiFi...")
#  connect to your SSID
wifi.radio.connect(os.getenv('CIRCUITPY_WIFI_SSID'), os.getenv('CIRCUITPY_WIFI_PASSWORD'))
print("Connected to WiFi!")

pool = socketpool.SocketPool(wifi.radio)
requests = adafruit_requests.Session(pool, ssl.create_default_context())

io = IO_HTTP(aio_username, aio_key, requests)

try:
    feed_lights = io.get_feed("lights")
except AdafruitIO_RequestError:
    feed_lights = io.create_new_feed("lights")

while True:
    try:
        if not button.value and button_state:
            button_state = False
        if button.value and not button_state:
            print("pressed")
            lights_on = not lights_on
            io.send_data(feed_lights["key"], int(lights_on))
            button_state = True
    except Exception as error: # pylint: disable=broad-except
        print(error)
        time.sleep(5)
        microcontroller.reset()
