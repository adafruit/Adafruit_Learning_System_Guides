# SPDX-FileCopyrightText: 2023 Brent Rubell for Adafruit Industries
# SPDX-License-Identifier: MIT
#
# An open-source IoT birdfeeder camera with Adafruit MEMENTO

import os
import ssl
import binascii
import board
import digitalio
import socketpool
import wifi
import adafruit_pycamera
import adafruit_requests
from adafruit_io.adafruit_io import IO_HTTP, AdafruitIO_RequestError

print("MEMENTO Birdfeeder Camera")

### WiFi ###
# Add settings.toml to your filesystem CIRCUITPY_WIFI_SSID and CIRCUITPY_WIFI_PASSWORD keys
# with your WiFi credentials. DO NOT share that file or commit it into Git or other
# source control.

# Set your Adafruit IO Username, Key and Port in settings.toml
# (visit io.adafruit.com if you need to create an account,
# or if you need your Adafruit IO key.)
aio_username = os.getenv("ADAFRUIT_AIO_USERNAME")
aio_key = os.getenv("ADAFRUIT_AIO_KEY")

#print(f"Connecting to {os.getenv('CIRCUITPY_WIFI_SSID')}")
wifi.radio.connect(os.getenv("CIRCUITPY_WIFI_SSID"), os.getenv("CIRCUITPY_WIFI_PASSWORD"))
#print(f"Connected to {os.getenv('CIRCUITPY_WIFI_SSID')}!")

pool = socketpool.SocketPool(wifi.radio)
requests = adafruit_requests.Session(pool, ssl.create_default_context())

# Initialize an Adafruit IO HTTP API object
io = IO_HTTP(aio_username, aio_key, requests)

try:
    # Get the 'birdfeeder' feed from Adafruit IO
    feed_camera = io.get_feed("birdfeeder")
except AdafruitIO_RequestError:
    # If no 'birdfeeder' feed exists, create one
    feed_camera = io.create_new_feed("birdfeeder")

# initialize camera
pycam = adafruit_pycamera.PyCamera()
# turn off the display backlight
pycam.display.brightness = 0.0
# set photo resolution
pycam.resolution = 3
# set focus to estimated bird location
pycam.autofocus_vcm_step = 145

# initialize PIR sensor
pir = digitalio.DigitalInOut(board.A0)
pir.direction = digitalio.Direction.INPUT

def send_jpeg_to_io():
    # before we send the image to IO, it needs to be encoded into base64
    encoded_data = binascii.b2a_base64(jpeg).strip().decode("utf-8")
    # then, send the encoded_data to Adafruit IO camera feed
    print("Sending image to IO...")
    io.send_data(feed_camera["key"], encoded_data)
    print("Sent image to IO!")

print("Waiting for movement...")
old_pir_value = pir.value
while True:
    pir_value = pir.value
    # if we detect movement, take a photo
    if pir_value:
        if not old_pir_value:
            print("Movement detected, taking picture!")
            # take a picture and save it into a jpeg bytes object
            jpeg = pycam.capture_into_jpeg()
            # if the camera successfully captured a jpeg, send it to IO
            if jpeg is not None:
                send_jpeg_to_io()
            else:
                print("ERROR: JPEG capture failed!")
    else:
        if old_pir_value:
            print("Movement ended")
        # update old_pir_value
    old_pir_value = pir_value
