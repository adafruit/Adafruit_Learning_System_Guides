# SPDX-FileCopyrightText: 2023 Liz Clark for Adafruit Industries
# SPDX-License-Identifier: MIT

"""Simple Adafruit IO Example for IoT Button with NeoPixel BFF"""
import os
import time
import ssl
import wifi
import socketpool
import microcontroller
import board
from digitalio import DigitalInOut, Direction, Pull
import neopixel
import adafruit_requests
from adafruit_io.adafruit_io import IO_HTTP, AdafruitIO_RequestError

# setup onboard button
switch = DigitalInOut(board.A2)
switch.direction = Direction.INPUT
switch.pull = Pull.UP

# setup onboard NeoPixel
pixel_pin = board.A3
num_pixels = 1

pixels = neopixel.NeoPixel(pixel_pin, num_pixels, brightness=0.3, auto_write=False)

# neopixel status colors
RED = (255, 0, 0)
GREEN = (0, 255, 0)
BLUE = (0, 0, 255)

# red until connecting
pixels.fill(RED)
pixels.show()

wifi.radio.connect(os.getenv('CIRCUITPY_WIFI_SSID'), os.getenv('CIRCUITPY_WIFI_PASSWORD'))

aio_username = os.getenv('aio_username')
aio_key = os.getenv('aio_key')

pool = socketpool.SocketPool(wifi.radio)
requests = adafruit_requests.Session(pool, ssl.create_default_context())
# Initialize an Adafruit IO HTTP API object
io = IO_HTTP(aio_username, aio_key, requests)
print("connected to io")
# blue when talking to IO
pixels.fill(BLUE)
pixels.show()

try:
    # get feed
    button_feed = io.get_feed("buttonbff")
except AdafruitIO_RequestError:
    # if no feed exists, create one
    button_feed = io.create_new_feed("buttonbff")

# green once connected
pixels.fill(GREEN)
pixels.show()

# button press count sent to IO
count = 0

while True:
    try:
		# if the button is pressed..
        if not switch.value:
            # blue when talking to IO
            pixels.fill(BLUE)
            pixels.show()
			# increase by 1 with press
            count += 1
			# send count to feed
            io.send_data(button_feed["key"], count)
            print("sent %d" % count)
            print()
			# delay
            time.sleep(5)
        else:
            # green if connected
            pixels.fill(GREEN)
            pixels.show()

    # pylint: disable=broad-except
    # any errors, reset board
    except Exception as e:
        # neopixels red with an error
        pixels.fill(RED)
        pixels.show()
        print("Error:\n", str(e))
        print("Resetting microcontroller in 10 seconds")
        time.sleep(10)
        microcontroller.reset()
