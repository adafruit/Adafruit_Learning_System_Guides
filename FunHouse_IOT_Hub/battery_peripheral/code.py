# SPDX-FileCopyrightText: 2021 Eva Herrada for Adafruit Industries
# SPDX-License-Identifier: MIT

"""
Adafruit IO connected LiPo charger.
Uses:
    * https://www.adafruit.com/product/4712
    * Feather board (M4 or RP2040 reccomended)
    * https://www.adafruit.com/product/4264
    * https://www.adafruit.com/product/2890
    * https://www.adafruit.com/product/2900
Either the Feather or the Airlift Featherwing should have stacking headers for the display.
"""

from os import getenv
import time
import board
from adafruit_lc709203f import LC709203F
import busio
from digitalio import DigitalInOut
import adafruit_connection_manager
from adafruit_esp32spi import adafruit_esp32spi
from adafruit_esp32spi import adafruit_esp32spi_wifimanager
import neopixel
import adafruit_minimqtt.adafruit_minimqtt as MQTT
from adafruit_io.adafruit_io import IO_MQTT

import displayio
import i2cdisplaybus
import terminalio
from adafruit_display_text import label
import adafruit_displayio_ssd1306

# Get WiFi details and Adafruit IO keys, ensure these are setup in settings.toml
# (visit io.adafruit.com if you need to create an account, or if you need your Adafruit IO key.)
ssid = getenv("CIRCUITPY_WIFI_SSID")
password = getenv("CIRCUITPY_WIFI_PASSWORD")
aio_username = getenv("ADAFRUIT_AIO_USERNAME")
aio_key = getenv("ADAFRUIT_AIO_KEY")

if None in [ssid, password, aio_username, aio_key]:
    raise RuntimeError(
        "WiFi and Adafruit IO settings are kept in settings.toml, "
        "please add them there. The settings file must contain "
        "'CIRCUITPY_WIFI_SSID', 'CIRCUITPY_WIFI_PASSWORD', "
        "'ADAFRUIT_AIO_USERNAME' and 'ADAFRUIT_AIO_KEY' at a minimum."
    )

displayio.release_displays()

### WiFi ###

# If you are using a board with pre-defined ESP32 Pins:
esp32_cs = DigitalInOut(board.D13)
esp32_ready = DigitalInOut(board.D11)
esp32_reset = DigitalInOut(board.D12)

spi = busio.SPI(board.SCK, board.MOSI, board.MISO)
esp = adafruit_esp32spi.ESP_SPIcontrol(spi, esp32_cs, esp32_ready, esp32_reset)
"""Use below for Most Boards"""
status_pixel = neopixel.NeoPixel(
    board.NEOPIXEL, 1, brightness=0.2
)  # Uncomment for Most Boards
wifi = adafruit_esp32spi_wifimanager.WiFiManager(esp, ssid, password, status_pixel=status_pixel)

# Define callback functions which will be called when certain events happen.
# pylint: disable=unused-argument
def connected(client):
    client.subscribe("battery")


def subscribe(client, userdata, topic, granted_qos):
    # This method is called when the client subscribes to a new feed.
    print("Subscribed to {0} with QOS level {1}".format(topic, granted_qos))


def message(client, feed_id, payload):
    print("Feed {0} received new value: {1}".format(feed_id, payload))


# Connect to WiFi
print("Connecting to WiFi...")
wifi.connect()
print("Connected!")

pool = adafruit_connection_manager.get_radio_socketpool(esp)
ssl_context = adafruit_connection_manager.get_radio_ssl_context(esp)

# Initialize a new MQTT Client object
mqtt_client = MQTT.MQTT(
    broker="io.adafruit.com",
    username=aio_username,
    password=aio_key,
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

i2c = board.I2C()  # uses board.SCL and board.SDA
# i2c = board.STEMMA_I2C()  # For using the built-in STEMMA QT connector on a microcontroller
display_bus = i2cdisplaybus.I2CDisplayBus(i2c, device_address=0x3C)

WIDTH = 128
HEIGHT = 32
BORDER = 2

display = adafruit_displayio_ssd1306.SSD1306(display_bus, width=WIDTH, height=HEIGHT)

splash = displayio.Group()
display.root_group = splash

digital_label = label.Label(
    terminalio.FONT, text="Battery Percent: ", color=0xFFFFFF, x=4, y=4
)
splash.append(digital_label)
alarm_label = label.Label(terminalio.FONT, text="Voltage: ", color=0xFFFFFF, x=4, y=14)
splash.append(alarm_label)


i2c = board.I2C()  # uses board.SCL and board.SDA
# i2c = board.STEMMA_I2C()  # For using the built-in STEMMA QT connector on a microcontroller
sensor = LC709203F(i2c)

start = 0
while True:
    io.loop()
    percent = sensor.cell_percent
    if time.time() - start > 60:
        io.publish("battery", int(percent))
        start = time.time()
    splash[0].text = f"Percent: {str(int(percent))}%"
    splash[1].text = f"Voltage: {str(sensor.cell_voltage)}"
    time.sleep(1)
