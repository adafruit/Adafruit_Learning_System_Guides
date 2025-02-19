# SPDX-FileCopyrightText: 2021 Eva Herrada for Adafruit Industries
# SPDX-License-Identifier: MIT

"""
Sets NeoPixel color based on an Adafruit IO feed.
Uses:
    * https://www.adafruit.com/product/3811
    * Feather board
    * https://www.adafruit.com/product/4264
    * https://www.adafruit.com/product/2890

If your Feather board has STEMMA QT, you'll need one of these:
    * https://www.adafruit.com/product/4209

But if it doesn't, use stacking headers on either the Feather or the AirLift FeatherWing
"""

import board
import busio
import adafruit_connection_manager
from adafruit_esp32spi import adafruit_esp32spi
from adafruit_esp32spi import adafruit_esp32spi_wifimanager
import neopixel
import adafruit_minimqtt.adafruit_minimqtt as MQTT
from adafruit_io.adafruit_io import IO_MQTT
from digitalio import DigitalInOut

### WiFi ###

# Get wifi details and more from a secrets.py file
try:
    from secrets import secrets
except ImportError:
    print("WiFi secrets are kept in secrets.py, please add them there!")
    raise

# Change the first number to the pin the data line is plugged in to and the second number
# to the number of pixels
pixels = neopixel.NeoPixel(board.D5, 300)

# If you are using a board with pre-defined ESP32 Pins:
esp32_cs = DigitalInOut(board.D13)
esp32_ready = DigitalInOut(board.D11)
esp32_reset = DigitalInOut(board.D12)

spi = busio.SPI(board.SCK, board.MOSI, board.MISO)
esp = adafruit_esp32spi.ESP_SPIcontrol(spi, esp32_cs, esp32_ready, esp32_reset)
"""Use below for Most Boards"""
status_light = neopixel.NeoPixel(
    board.NEOPIXEL, 1, brightness=0.2
)  # Uncomment for Most Boards
wifi = adafruit_esp32spi_wifimanager.ESPSPI_WiFiManager(esp, secrets, status_light)

# Define callback functions which will be called when certain events happen.
# pylint: disable=unused-argument
def connected(client):
    client.subscribe("neopixel")


def subscribe(client, userdata, topic, granted_qos):
    # This method is called when the client subscribes to a new feed.
    print("Subscribed to {0} with QOS level {1}".format(topic, granted_qos))


def on_neopixel(client, topic, message):
    print(message)
    colors = [
        int(message.split("#")[1][i : i + 2], 16) for i in range(0, len(message) - 1, 2)
    ]
    print(colors)
    pixels.fill(colors)


# Connect to WiFi
print("Connecting to WiFi...")
wifi.connect()
print("Connected!")

pool = adafruit_connection_manager.get_radio_socketpool(esp)
ssl_context = adafruit_connection_manager.get_radio_ssl_context(esp)

# Initialize a new MQTT Client object
mqtt_client = MQTT.MQTT(
    broker="io.adafruit.com",
    username=secrets["aio_username"],
    password=secrets["aio_key"],
    socket_pool=pool,
    ssl_context=ssl_context,
)


# Initialize an Adafruit IO MQTT Client
io = IO_MQTT(mqtt_client)

io.add_feed_callback("neopixel", on_neopixel)
# Connect the callback methods defined above to Adafruit IO
io.on_connect = connected
io.on_subscribe = subscribe

# Connect to Adafruit IO
print("Connecting to Adafruit IO...")
io.connect()

io.get("neopixel")

while True:
    io.loop()
