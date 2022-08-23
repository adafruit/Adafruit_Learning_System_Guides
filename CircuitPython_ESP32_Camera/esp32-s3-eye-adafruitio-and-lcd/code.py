# SPDX-FileCopyrightText: Copyright (c) 2021 Jeff Epler for Adafruit Industries
#
# SPDX-License-Identifier: Unlicense

"""
Show the live camera image on the viewfinder, then upload to adafruit IO when
the 'BOOT' button is pressed.
"""

import binascii
import ssl
import struct

from adafruit_io.adafruit_io import IO_MQTT
import adafruit_minimqtt.adafruit_minimqtt as MQTT
import board
import dotenv
import esp32_camera
import keypad
import socketpool
import wifi

shutter_button = keypad.Keys((board.BOOT,), value_when_pressed=False)

aio_username = dotenv.get_key("/.env", "AIO_USERNAME")
aio_key = dotenv.get_key("/.env", "AIO_KEY")

image_feed = "image"

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


print("Initializing camera")
cam = esp32_camera.Camera(
    data_pins=board.CAMERA_DATA,
    external_clock_pin=board.CAMERA_XCLK,
    pixel_clock_pin=board.CAMERA_PCLK,
    vsync_pin=board.CAMERA_VSYNC,
    href_pin=board.CAMERA_HREF,
    pixel_format=esp32_camera.PixelFormat.RGB565,
    frame_size=esp32_camera.FrameSize.R240X240,
    i2c=board.I2C(),
    external_clock_frequency=20_000_000,
    framebuffer_count=2,
)
cam.vflip = True
cam.hmirror = True

board.DISPLAY.auto_refresh = False
display_bus = board.DISPLAY.bus

print(cam.width, cam.height)

ow = (board.DISPLAY.width - cam.width) // 2
oh = (board.DISPLAY.height - cam.height) // 2
display_bus.send(42, struct.pack(">hh", ow, cam.width + ow - 1))
display_bus.send(43, struct.pack(">hh", oh, cam.height + ow - 1))

while True:
    frame = cam.take(1)
    display_bus.send(44, frame)
    if (ev := shutter_button.events.get()) and ev.pressed:
        cam.reconfigure(
            pixel_format=esp32_camera.PixelFormat.JPEG,
            frame_size=esp32_camera.FrameSize.SVGA,
        )
        frame = cam.take(1)
        if isinstance(frame, memoryview):
            jpeg = frame
            print(f"Captured {len(jpeg)} bytes of jpeg data")

            # b2a_base64() appends a trailing newline, which IO does not like
            encoded_data = binascii.b2a_base64(jpeg).strip()
            print(f"Expanded to {len(encoded_data)} for IO upload")

            io.publish("image", encoded_data)
        cam.reconfigure(
            pixel_format=esp32_camera.PixelFormat.RGB565,
            frame_size=esp32_camera.FrameSize.R240X240,
        )
    print(end=".")
