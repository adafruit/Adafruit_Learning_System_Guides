# SPDX-FileCopyrightText: 2021 Ladyada for Adafruit Industries
# SPDX-FileCopyrightText: 2022 Kattni Rembor for Adafruit Industries
# SPDX-License-Identifier: MIT
import time
import ssl
import socketpool
import wifi
import board
import neopixel
import microcontroller
import adafruit_minimqtt.adafruit_minimqtt as MQTT
from adafruit_io.adafruit_io import IO_MQTT

try:
    from secrets import secrets
except ImportError:
    print("WiFi and Adafruit IO credentials are kept in secrets.py - please add them there!")
    raise

# Add your Adafruit IO Username and Key to secrets.py
# (visit io.adafruit.com if you need to create an account,
# or if you need your Adafruit IO key.)
aio_username = secrets["aio_username"]
aio_key = secrets["aio_key"]

# WiFi
print("Connecting to %s" % secrets["ssid"])
wifi.radio.connect(secrets["ssid"], secrets["password"])
print("Connected to %s!" % secrets["ssid"])

# Initialize NeoPixel
pixel = neopixel.NeoPixel(board.NEOPIXEL, 1, brightness=0.3)


# Define callback functions which will be called when certain events happen.
# pylint: disable=unused-argument
def connected(client):
    print("Connected to Adafruit IO!  Listening for NeoPixel changes...")
    # Subscribe to Adafruit IO feed called "neopixel"
    client.subscribe("neopixel")


# pylint: disable=unused-argument
def message(client, feed_id, payload):
    print("Feed {0} received new value: {1}".format(feed_id, payload))
    if feed_id == "neopixel":
        pixel.fill(int(payload[1:], 16))


# Create a socket pool
pool = socketpool.SocketPool(wifi.radio)

# Initialize a new MQTT Client object
mqtt_client = MQTT.MQTT(
    broker="io.adafruit.com",
    username=secrets["aio_username"],
    password=secrets["aio_key"],
    socket_pool=pool,
    ssl_context=ssl.create_default_context(),
)

# Initialize Adafruit IO MQTT "helper"
io = IO_MQTT(mqtt_client)

# Set up the callback methods above
io.on_connect = connected
io.on_message = message

# Connect the client to the MQTT broker.
print("Connecting to Adafruit IO...")
io.connect()

timestamp = 0
while True:
    # Explicitly pump the message loop.
    io.loop()

    # Obtain the CPU temperature, print it and publish it to Adafruit IO every 10 seconds.
    if (time.monotonic() - timestamp) >= 10:
        temperature = "{:.2f}".format(microcontroller.cpu.temperature)
        print("Current CPU temperature: {0} C".format(temperature))
        io.publish("cpu-temperature", temperature)
        timestamp = time.monotonic()
