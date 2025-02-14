# SPDX-FileCopyrightText: 2024 Liz Clark for Adafruit Industries
#
# SPDX-License-Identifier: MIT

import time
import os
import ssl
import io
import binascii
import jpegio
import microcontroller
import wifi
import socketpool
import displayio
from adafruit_qualia.graphics import Graphics, Displays
import adafruit_minimqtt.adafruit_minimqtt as MQTT

aio_username = os.getenv("ADAFRUIT_AIO_USERNAME")
aio_key = os.getenv("ADAFRUIT_AIO_KEY")

print(f"Connecting to {os.getenv('CIRCUITPY_WIFI_SSID')}")
wifi.radio.connect(os.getenv("CIRCUITPY_WIFI_SSID"), os.getenv("CIRCUITPY_WIFI_PASSWORD"))
print(f"Connected to {os.getenv('CIRCUITPY_WIFI_SSID')}!")

camera_feed = aio_username + "/feeds/camera"

graphics = Graphics(Displays.ROUND40, default_bg=None, auto_refresh=True)

def center(g, b):
    # center the image
    g.x -= ((b.width * 2) - 720) // 4
    g.y -= ((b.height * 2) - 720) // 4

def decode_image(base64_msg):
    # Decode the base64 image into raw binary JPEG data
    decoded_image = binascii.a2b_base64(base64_msg)
    # Create a JpegDecoder instance
    decoder = jpegio.JpegDecoder()
    # Use io.BytesIO to treat the decoded image as a file-like object
    jpeg_data = io.BytesIO(decoded_image)
    # Open the JPEG data source from the BytesIO object
    width, height = decoder.open(jpeg_data)
    print(width, height)
    # Create a Bitmap with the dimensions of the JPEG image
    bitmap = displayio.Bitmap(width, height, 65536)  # Use 65536 colors for RGB565
    # Decode the JPEG into the bitmap
    decoder.decode(bitmap)
    # pylint: disable=line-too-long
    grid = displayio.TileGrid(bitmap, pixel_shader=displayio.ColorConverter(input_colorspace=displayio.Colorspace.RGB565_SWAPPED))
    center(grid, bitmap)
    group = displayio.Group(scale=2)
    group.append(grid)
    graphics.display.root_group = group
    graphics.display.refresh()


# Define callback methods which are called when events occur
def connected(client, userdata, flags, rc): # pylint: disable=unused-argument
    # This function will be called when the client is connected
    # successfully to the broker.
    print(f"Connected to Adafruit IO! Listening for topic changes on {camera_feed}")
    # Subscribe to all changes on the onoff_feed.
    client.subscribe(camera_feed)


def disconnected(client, userdata, rc): # pylint: disable=unused-argument
    # This method is called when the client is disconnected
    print("Disconnected from Adafruit IO!")


def message(client, topic, msg): # pylint: disable=unused-argument
    # This method is called when a topic the client is subscribed to
    # has a new message.
    print(f"New message on topic {topic}")
    decode_image(msg)

pool = socketpool.SocketPool(wifi.radio)
ssl_context = ssl.create_default_context()
# Initialize an Adafruit IO HTTP API object
mqtt_client = MQTT.MQTT(
    broker="io.adafruit.com",
    port=1883,
    username=aio_username,
    password=aio_key,
    socket_pool=pool,
    ssl_context=ssl_context,
)
# Setup the callback methods above
mqtt_client.on_connect = connected
mqtt_client.on_disconnect = disconnected
mqtt_client.on_message = message

# Connect the client to the MQTT broker.
print("Connecting to Adafruit IO...")
mqtt_client.connect()
while True:
    # Poll the message queue
    try:
        mqtt_client.loop(timeout=1)
        time.sleep(5)
    except Exception as error: # pylint: disable=broad-except
        print(error)
        time.sleep(5)
        microcontroller.reset()
