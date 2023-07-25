# SPDX-FileCopyrightText: 2021 Ladyada for Adafruit Industries
# SPDX-FileCopyrightText: 2022 Kattni Rembor for Adafruit Industries
# SPDX-License-Identifier: MIT
import time
import ssl
import os
from random import randint
import microcontroller
import socketpool
import wifi
import board
import neopixel
import adafruit_minimqtt.adafruit_minimqtt as MQTT
from adafruit_io.adafruit_io import IO_MQTT


# WiFi
try:
    print("Connecting to %s" % os.getenv("WIFI_SSID"))
    wifi.radio.connect(os.getenv("WIFI_SSID"), os.getenv("WIFI_PASSWORD"))
    print("Connected to %s!" % os.getenv("WIFI_SSID"))
# Wi-Fi connectivity fails with error messages, not specific errors, so this except is broad.
except Exception as e:  # pylint: disable=broad-except
    print("Failed to connect to WiFi. Error:", e, "\nBoard will hard reset in 30 seconds.")
    time.sleep(30)
    microcontroller.reset()

# Initialise NeoPixel
pixel = neopixel.NeoPixel(board.NEOPIXEL, 1, brightness=0.3)


# Define callback functions which will be called when certain events happen.
def connected(client):
    print("Connected to Adafruit IO!  Listening for NeoPixel changes...")
    # Subscribe to Adafruit IO feed called "neopixel"
    client.subscribe("neopixel")


def message(client, feed_id, payload):  # pylint: disable=unused-argument
    print("Feed {0} received new value: {1}".format(feed_id, payload))
    if feed_id == "neopixel":
        pixel.fill(int(payload[1:], 16))


# Create a socket pool
pool = socketpool.SocketPool(wifi.radio)

# Initialize a new MQTT Client object
mqtt_client = MQTT.MQTT(
    broker="io.adafruit.com",
    username=os.getenv("AIO_USERNAME"),
    password=os.getenv("AIO_KEY"),
    socket_pool=pool,
    ssl_context=ssl.create_default_context(),
)

# Initialize Adafruit IO MQTT "helper"
io = IO_MQTT(mqtt_client)

# Set up the callback methods above
io.on_connect = connected
io.on_message = message

timestamp = 0
while True:
    try:
        # If Adafruit IO is not connected...
        if not io.is_connected:
            # Connect the client to the MQTT broker.
            print("Connecting to Adafruit IO...")
            io.connect()

        # Explicitly pump the message loop.
        io.loop()
        # Obtain the "random" value, print it and publish it to Adafruit IO every 10 seconds.
        if (time.monotonic() - timestamp) >= 10:
            random_number = "{}".format(randint(0, 255))
            print("Current 'random' number: {}".format(random_number))
            io.publish("random", random_number)
            timestamp = time.monotonic()

    # Adafruit IO fails with internal error types and WiFi fails with specific messages.
    # This except is broad to handle any possible failure.
    except Exception as e:  # pylint: disable=broad-except
        print("Failed to get or send data, or connect. Error:", e,
              "\nBoard will hard reset in 30 seconds.")
        time.sleep(30)
        microcontroller.reset()
