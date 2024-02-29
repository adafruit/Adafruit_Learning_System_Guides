# SPDX-FileCopyrightText: 2021 Eva Herrada for Adafruit Industries
# SPDX-License-Identifier: MIT

"""
Controlling a relay with Adafruit IO
Uses:
    * Feather board
    * https://www.adafruit.com/product/2890
    * https://www.adafruit.com/product/4264

    * https://www.adafruit.com/product/3191
    OR
    * https://www.adafruit.com/product/2935
"""
import board
import busio
import adafruit_connection_manager
from adafruit_esp32spi import adafruit_esp32spi
from adafruit_esp32spi import adafruit_esp32spi_wifimanager
import adafruit_esp32spi.adafruit_esp32spi_socket as pool
import neopixel
import adafruit_minimqtt.adafruit_minimqtt as MQTT
from adafruit_io.adafruit_io import IO_MQTT
from digitalio import DigitalInOut, Direction

### WiFi ###

# Get wifi details and more from a secrets.py file
try:
    from secrets import secrets
except ImportError:
    print("WiFi secrets are kept in secrets.py, please add them there!")
    raise

# If you are using a Relay FeatherWing, make sure this pin corresponds to the pin shorted on the
# bottom of the Relay FeatherWing
RELAY = DigitalInOut(board.D10)
RELAY.direction = Direction.OUTPUT

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
    client.subscribe("lamp")


def subscribe(client, userdata, topic, granted_qos):
    # This method is called when the client subscribes to a new feed.
    print("Subscribed to {0} with QOS level {1}".format(topic, granted_qos))


def on_lamp(client, topic, message):
    RELAY.value = eval(message)  # pylint: disable=eval-used


# Connect to WiFi
print("Connecting to WiFi...")
wifi.connect()
print("Connected!")

ssl_context = adafruit_connection_manager.create_fake_ssl_context(pool, esp)

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

io.add_feed_callback("lamp", on_lamp)
# Connect the callback methods defined above to Adafruit IO
io.on_connect = connected
io.on_subscribe = subscribe

# Connect to Adafruit IO
print("Connecting to Adafruit IO...")
io.connect()

io.get("lamp")

while True:
    io.loop()
