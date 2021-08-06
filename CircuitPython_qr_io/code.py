# SPDX-FileCopyrightText: Copyright (c) 2021 Jeff Epler for Adafruit Industries
#
# SPDX-License-Identifier: Unlicense

"""
This demo is designed for the Kaluga development kit version 1.3 with the
ILI9341 display.  Your secrets.py must be populated with your wifi credentials
and your Adafruit IO credentials.
"""

import ssl
from secrets import secrets
from ulab import numpy as np
from terminalio import FONT
import board
import busio
import displayio
import qrio
import socketpool
import wifi
import adafruit_ov2640
from adafruit_display_text.bitmap_label import Label
from adafruit_ili9341 import ILI9341
from adafruit_io.adafruit_io import IO_MQTT
import adafruit_minimqtt.adafruit_minimqtt as MQTT

# To change the name of the feed on adafruit_io, just modify this string:
feed_name = "qrstring"

print("Initializing display")
displayio.release_displays()
spi = busio.SPI(MOSI=board.LCD_MOSI, clock=board.LCD_CLK)
display_bus = displayio.FourWire(
    spi, command=board.LCD_D_C, chip_select=board.LCD_CS, reset=board.LCD_RST
)
display = ILI9341(display_bus, width=320, height=240, rotation=90)

print("Initializing camera")
bus = busio.I2C(scl=board.CAMERA_SIOC, sda=board.CAMERA_SIOD)
cam = adafruit_ov2640.OV2640(
    bus,
    data_pins=board.CAMERA_DATA,
    clock=board.CAMERA_PCLK,
    vsync=board.CAMERA_VSYNC,
    href=board.CAMERA_HREF,
    mclk=board.CAMERA_XCLK,
    mclk_frequency=20_000_000,
    size=adafruit_ov2640.OV2640_SIZE_QQVGA,
)
cam.flip_x = False
cam.flip_y = False
cam.colorspace = adafruit_ov2640.OV2640_COLOR_YUV

print("Connecting to WIFI")
wifi.radio.connect(secrets["ssid"], secrets["password"])
pool = socketpool.SocketPool(wifi.radio)

print("Connecting to Adafruit IO")
mqtt_client = MQTT.MQTT(
    broker="io.adafruit.com",
    username=secrets["aio_username"],
    password=secrets["aio_key"],
    socket_pool=pool,
    ssl_context=ssl.create_default_context(),
)
mqtt_client.connect()
io = IO_MQTT(mqtt_client)
# Blank out any previously published message
io.publish(feed_name, "\ufeff")

qrdecoder = qrio.QRDecoder(cam.width, cam.height)
bitmap = displayio.Bitmap(cam.width, cam.height, 65536)

# Create a greyscale palette
pal = displayio.Palette(256)
for i in range(256):
    pal[i] = 0x10101 * i

label = Label(
    font=FONT,
    text="Scan QR Code...",
    color=0xFFFFFF,
    background_color=0x0,
    padding_top=2,
    padding_left=2,
    padding_right=2,
    padding_bottom=2,
    anchor_point=(0.5, 1.0),
    anchored_position=(160, 230),
)
# Show the camera image at 2x size
g1 = displayio.Group(scale=2)
view = np.frombuffer(bitmap, dtype=np.uint8)
tg = displayio.TileGrid(
    bitmap,
    pixel_shader=pal,
)
tg.flip_y = True
g1.append(tg)
g = displayio.Group()
g.append(g1)
g.append(label)
display.show(g)
display.auto_refresh = False

old_payload = None
while True:
    cam.capture(bitmap)

    for row in qrdecoder.decode(bitmap, qrio.PixelPolicy.EVEN_BYTES):
        payload = row.payload
        try:
            payload = payload.decode("utf-8")
        except UnicodeError:
            payload = str(payload)
        if payload != old_payload:
            label.text = payload
            print(payload)
            for i in range(3):
                try:
                    io.publish(feed_name, payload)
                    old_payload = payload
                    break
                except OSError as e:
                    print(e)
                    mqtt_client.reconnect()

    # Clear out the odd bytes, so that the bitmap displays as greyscale
    view[1::2] = 0
    bitmap.dirty()
    display.refresh(minimum_frames_per_second=0)
