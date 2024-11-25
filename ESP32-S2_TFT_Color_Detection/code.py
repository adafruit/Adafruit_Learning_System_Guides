# SPDX-FileCopyrightText: 2024 Trevor Beaton for Adafruit Industries
#
# SPDX-License-Identifier: MIT
'''This is a program for a color detection project using the APD-9960 and Feather ESP32-S2 & S3'''

import os
import ssl
import time
import wifi
import board
import busio
import socketpool
import adafruit_requests
from adafruit_apds9960.apds9960 import APDS9960
from adafruit_io.adafruit_io import IO_HTTP, AdafruitIO_RequestError

# WiFi and Adafruit IO setup
aio_username = os.getenv("aio_username")
aio_key = os.getenv("aio_key")

wifi.radio.connect(
    os.getenv("CIRCUITPY_WIFI_SSID"), os.getenv("CIRCUITPY_WIFI_PASSWORD")
)
print(f"Connected to {os.getenv('CIRCUITPY_WIFI_SSID')}!")

# Initialize network pool and Adafruit IO HTTP
pool = socketpool.SocketPool(wifi.radio)
requests = adafruit_requests.Session(pool, ssl.create_default_context())
io = IO_HTTP(aio_username, aio_key, requests)

# Set up I2C connection and APDS9960 sensor
i2c = busio.I2C(board.SCL, board.SDA)
apds = APDS9960(i2c)
apds.enable_proximity = True
apds.enable_color = True

# Adafruit IO feed setup
try:
    hue_feed = io.get_feed("hue")
except AdafruitIO_RequestError:
    hue_feed = io.create_new_feed("hue")


# Function to convert RGB to Hue
def rgb_to_hue(r: int, g: int, b: int) -> float:
    r_norm = r / 255.0
    g_norm = g / 255.0
    b_norm = b / 255.0
    c_max = max(r_norm, g_norm, b_norm)
    c_min = min(r_norm, g_norm, b_norm)
    delta = c_max - c_min

    if delta == 0:
        calculated_hue = 0
    elif c_max == r_norm:
        calculated_hue = (60 * ((g_norm - b_norm) / delta) + 360) % 360
    elif c_max == g_norm:
        calculated_hue = (60 * ((b_norm - r_norm) / delta) + 120) % 360
    elif c_max == b_norm:
        calculated_hue = (60 * ((r_norm - g_norm) / delta) + 240) % 360
    else:
        calculated_hue = 0  # Fallback case

    return calculated_hue


# Main loop
while True:
    color_data = apds.color_data
    red_value, green_value, blue_value = color_data[0], color_data[1], color_data[2]
    hue_value = round(rgb_to_hue(red_value, green_value, blue_value))
    print(f"Detected Hue: {hue_value}")

    try:
        io.send_data(hue_feed["key"], hue_value)
        print(f"Sent Hue value {hue_value} to Adafruit IO feed 'hue'")
    except AdafruitIO_RequestError as e:
        print(f"Error sending data: {e}")

    time.sleep(3)
