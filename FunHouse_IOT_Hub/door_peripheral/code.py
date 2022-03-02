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

import board
import busio
from adafruit_esp32spi import adafruit_esp32spi
from adafruit_esp32spi import adafruit_esp32spi_wifimanager
import adafruit_esp32spi.adafruit_esp32spi_socket as socket
import neopixel
import adafruit_minimqtt.adafruit_minimqtt as MQTT
from adafruit_io.adafruit_io import IO_MQTT
from digitalio import DigitalInOut, Direction, Pull
from adafruit_debouncer import Debouncer

### WiFi ###

# Get wifi details and more from a secrets.py file
try:
    from secrets import secrets
except ImportError:
    print("WiFi secrets are kept in secrets.py, please add them there!")
    raise

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
status_light = neopixel.NeoPixel(
    board.NEOPIXEL, 1, brightness=0.2
)  # Uncomment for Most Boards
wifi = adafruit_esp32spi_wifimanager.ESPSPI_WiFiManager(esp, secrets, status_light)

# Connect to WiFi
print("Connecting to WiFi...")
wifi.connect()
print("Connected!")

# Initialize MQTT interface with the esp interface
MQTT.set_socket(socket, esp)

# Initialize a new MQTT Client object
mqtt_client = MQTT.MQTT(
    broker="io.adafruit.com",
    username=secrets["aio_username"],
    password=secrets["aio_key"],
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
