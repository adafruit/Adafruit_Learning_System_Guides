# SPDX-FileCopyrightText: 2021 Eva Herrada for Adafruit Industries
# SPDX-License-Identifier: MIT

"""
Adafruit IO connected door sensor.
Uses:
    * https://www.adafruit.com/product/375
    * Feather board
    * https://www.adafruit.com/product/2890
    * https://www.adafruit.com/product/4264
    * https://www.adafruit.com/product/3786

This isn't necessary, but it makes it easier to connect the sensor to the Microcontroller if
either the Feather or the AirLift Featherwing has stacking headers.
"""

from os import getenv
import board
import busio
import adafruit_connection_manager
from adafruit_esp32spi import adafruit_esp32spi
from adafruit_esp32spi import adafruit_esp32spi_wifimanager
import neopixel
import adafruit_minimqtt.adafruit_minimqtt as MQTT
from adafruit_io.adafruit_io import IO_MQTT
from digitalio import DigitalInOut, Direction, Pull
from adafruit_debouncer import Debouncer

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

### WiFi ###

switch_pin = DigitalInOut(board.D10)
switch_pin.direction = Direction.INPUT
switch_pin.pull = Pull.UP
switch = Debouncer(switch_pin)

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

# Connect to Adafruit IO
print("Connecting to Adafruit IO...")
io.connect()

while True:
    switch.update()
    print(switch.state)

    if switch.rose:
        print("Door is open")
        io.publish("door", 0)
        print("sent")

    if switch.fell:
        print("Door is closed")
        io.publish("door", 1)
        print("sent")
