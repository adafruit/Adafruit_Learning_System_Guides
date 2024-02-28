# SPDX-FileCopyrightText: 2021 Eva Herrada for Adafruit Industries
# SPDX-License-Identifier: MIT

import time

import board
from digitalio import DigitalInOut
import adafruit_connection_manager
from adafruit_esp32spi import adafruit_esp32spi
from adafruit_esp32spi import adafruit_esp32spi_wifimanager
import adafruit_esp32spi.adafruit_esp32spi_socket as pool
import neopixel
import adafruit_minimqtt.adafruit_minimqtt as MQTT
from adafruit_io.adafruit_io import IO_MQTT
from adafruit_seesaw.seesaw import Seesaw
import busio

# Used to make sure that the Adafruit IO Trigger is only run once when the moisture value is below
# the desired threshold, set in MIN
LOW = False
# The minimum moisture value. If the value is below this number, it will activate the Adafruit IO
# trigger. This number should match the number you set in your Adafruit IO trigger. Feel free
# to mess around and try out different moisture values as how wet this actually is can vary a lot
# depending on where the sensor is and the soil in the pot.
MIN = 500

# Set up moisture sensor with seesaw
i2c = board.I2C()  # uses board.SCL and board.SDA
# i2c = board.STEMMA_I2C()  # For using the built-in STEMMA QT connector on a microcontroller
seesaw = Seesaw(i2c, addr=0x36)

# Get wifi details and more from a secrets.py file
try:
    from secrets import secrets
except ImportError:
    print("WiFi secrets are kept in secrets.py, please add them there!")
    raise

# Set up WiFi
esp32_cs = DigitalInOut(board.D13)
esp32_ready = DigitalInOut(board.D11)
esp32_reset = DigitalInOut(board.D12)

spi = busio.SPI(board.SCK, board.MOSI, board.MISO)
esp = adafruit_esp32spi.ESP_SPIcontrol(spi, esp32_cs, esp32_ready, esp32_reset)
status_light = neopixel.NeoPixel(board.NEOPIXEL, 1, brightness=0.2)
wifi = adafruit_esp32spi_wifimanager.ESPSPI_WiFiManager(esp, secrets, status_light)

# Define callback functions which will be called when certain events happen.
# pylint: disable=unused-argument
def connected(client):
    # This method is called when the client connects to Adafruit IO
    client.subscribe("plant")


def subscribe(client, userdata, topic, granted_qos):
    # This method is called when the client subscribes to a new feed.
    print("Subscribed to {0} with QOS level {1}".format(topic, granted_qos))


def message(client, feed_id, payload):
    # This method is called when a feed receives a new message
    print("Feed {0} received new value: {1}".format(feed_id, payload))


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

# Connect the callback methods defined above to Adafruit IO
io.on_connect = connected
io.on_subscribe = subscribe
io.on_message = message

# Connect to Adafruit IO
print("Connecting to Adafruit IO...")
io.connect()
plant_feed = "plant"

START = 0

while True:
    # read moisture level through capacitive touch pad
    touch = seesaw.moisture_read()

    # read temperature from the temperature sensor
    temp = seesaw.get_temp()

    if touch < MIN:
        if not LOW:
            io.publish(plant_feed, touch)
            print("published")
        LOW = True

    elif touch >= MIN and time.time() - START > 10:
        io.publish(plant_feed, touch)
        print("published to Adafruit IO")
        START = time.time()
        LOW = False

    print("temp: " + str(temp) + "  moisture: " + str(touch))
    time.sleep(1)
