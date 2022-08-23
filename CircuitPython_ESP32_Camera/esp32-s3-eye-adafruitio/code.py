# SPDX-FileCopyrightText: 2017 Scott Shawcroft, written for Adafruit Industries
# SPDX-FileCopyrightText: Copyright (c) 2021 Jeff Epler for Adafruit Industries
#
# SPDX-License-Identifier: Unlicense

"""
Upload a jpeg image to Adafruit IO at regular intervals

This example requires:
 * ESP32-S3-EYE development kit from Espressif

To use:
 * On io.adafruit.com, create a feed named "image" and turn OFF history
 * On io.adafruit.com, create a dashboard and add an "image" block
   using the feed "image" as its data
 * Set up CIRCUITPY/.env with WiFI and Adafruit IO credentials
 * Copy the project bundle to CIRCUITPY
"""

import binascii
import io
import ssl
import time
import adafruit_minimqtt.adafruit_minimqtt as MQTT
from adafruit_io.adafruit_io import IO_MQTT
import board
import dotenv
import esp32_camera
import socketpool
import wifi

aio_username = dotenv.get_key('/.env', 'AIO_USERNAME')
aio_key = dotenv.get_key('/.env', 'AIO_KEY')

image_feed = "image"

cam = esp32_camera.Camera(
    data_pins=board.CAMERA_DATA,
    external_clock_pin=board.CAMERA_XCLK,
    pixel_clock_pin=board.CAMERA_PCLK,
    vsync_pin=board.CAMERA_VSYNC,
    href_pin=board.CAMERA_HREF,
    pixel_format=esp32_camera.PixelFormat.JPEG,
    frame_size=esp32_camera.FrameSize.SVGA,
    i2c=board.I2C(),
    external_clock_frequency=20_000_000,
    grab_mode=esp32_camera.GrabMode.WHEN_EMPTY)
cam.vflip = True


pool = socketpool.SocketPool(wifi.radio)

print("Connecting to Adafruit IO")
mqtt_client = MQTT.MQTT(
    broker="io.adafruit.com",
    username=aio_username,
    password=aio_key,
    socket_pool=pool,
    ssl_context=ssl.create_default_context(),
)
mqtt_client.connect()
io = IO_MQTT(mqtt_client)

while True:
    frame = cam.take(1)
    if isinstance(frame, memoryview):
        jpeg = frame
        print(f"Captured {len(jpeg)} bytes of jpeg data")

        # b2a_base64() appends a trailing newline, which IO does not like
        encoded_data = binascii.b2a_base64(jpeg).strip()
        print(f"Expanded to {len(encoded_data)} for IO upload")

        io.publish("image", encoded_data)

        time.sleep(10)
