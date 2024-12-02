# SPDX-FileCopyrightText: 2024 Trevor Beaton for Adafruit Industries
#
# SPDX-License-Identifier: MIT
'''This is a program for a color detection project using the AS7341 and Feather ESP32-S2 & S3'''

import os
import ssl
import time
import wifi
import board
import busio
import socketpool
import adafruit_requests
import adafruit_as7341
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

# Set up I2C connection and AS7341 sensor
i2c = busio.I2C(board.SCL, board.SDA)
sensor = adafruit_as7341.AS7341(i2c)

# Configure the sensor with correct gain setting
sensor.gain = adafruit_as7341.Gain.GAIN_64X
sensor.atime = 100
sensor.astep = 999

# Adafruit IO feed setup
try:
    hue_feed = io.get_feed("hue")
except AdafruitIO_RequestError:
    hue_feed = io.create_new_feed("hue")

def spectral_to_rgb(ch1, ch2, ch3, ch4, ch5, ch6, ch7, ch8):
    # Normalize the channel readings
    total = ch1 + ch2 + ch3 + ch4 + ch5 + ch6 + ch7 + ch8
    if total == 0:
        total = 1
    ch1 /= total
    ch2 /= total
    ch3 /= total
    ch4 /= total
    ch5 /= total
    ch6 /= total
    ch7 /= total
    ch8 /= total

    # Map channels to RGB components
    red = ch6 + ch7 + ch8    # Orange, Red, Deep Red
    green = ch4 + ch5        # Green, Yellow-Green
    blue = ch1 + ch2 + ch3   # Violet, Blue, Blue-Green

    # Normalize RGB components
    rgb_total = red + green + blue
    if rgb_total == 0:
        rgb_total = 1
    red /= rgb_total
    green /= rgb_total
    blue /= rgb_total

    # Scale to 0-255 range
    red = int(min(max(red * 255, 0), 255))
    green = int(min(max(green * 255, 0), 255))
    blue = int(min(max(blue * 255, 0), 255))
    return red, green, blue

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
        calculated_hue = 0
    return calculated_hue

# Main loop
while True:
    # Read all spectral channels
    channel_readings = sensor.all_channels
    # Extract individual channel readings
    f1 = channel_readings[0]
    f2 = channel_readings[1]
    f3 = channel_readings[2]
    f4 = channel_readings[3]
    f5 = channel_readings[4]
    f6 = channel_readings[5]
    f7 = channel_readings[6]
    f8 = channel_readings[7]

    red_value, green_value, blue_value = spectral_to_rgb(f1, f2, f3, f4, f5, f6, f7, f8)
    hue_value = round(rgb_to_hue(red_value, green_value, blue_value))
    print(f"Detected Hue: {hue_value}")

    try:
        io.send_data(hue_feed["key"], hue_value)
        print(f"Sent Hue value {hue_value} to Adafruit IO feed 'hue'")
    except AdafruitIO_RequestError as e:
        print(f"Error sending data: {e}")
    time.sleep(4)
