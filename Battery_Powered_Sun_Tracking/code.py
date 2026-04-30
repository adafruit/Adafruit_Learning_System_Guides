# SPDX-FileCopyrightText: 2026 Adafruit Industries
# SPDX-License-Identifier: MIT

"""
Outdoor Light Logger -- Adafruit ESP32-S2 Feather + VEML7700

Reads ambient light in lux, sends the value to an Adafruit IO feed,
then enters deep sleep to save battery. On wake the board resets
and the script runs again from the top.

Required hardware:
  - Adafruit ESP32-S2 Feather
  - Adafruit VEML7700 Lux Sensor (STEMMA QT / I2C)

Required libraries in the /lib folder:
  - adafruit_veml7700.mpy
  - adafruit_requests.mpy
  - adafruit_connection_manager.mpy
  - adafruit_io (folder)
  - adafruit_minimqtt (folder)

Required entries in settings.toml:
  CIRCUITPY_WIFI_SSID = "your-wifi-name"
  CIRCUITPY_WIFI_PASSWORD = "your-wifi-password"
  ADAFRUIT_AIO_USERNAME = "your-aio-username"
  ADAFRUIT_AIO_KEY = "your-aio-key"
"""

import board
import time
import alarm
import wifi
import adafruit_connection_manager
import adafruit_requests
import adafruit_veml7700
from os import getenv
from adafruit_io.adafruit_io import IO_HTTP

# -- Settings --
SLEEP_INTERVAL = 300  # seconds between readings (5 minutes)
FEED_NAME = "ambient-light"  # must match your Adafruit IO feed key

# -- Hardware setup (once, outside the loop) --
i2c = board.I2C()
veml = adafruit_veml7700.VEML7700(i2c)
time.sleep(0.5)  # wait for first integration cycle to complete

while True:
    try:
        # -- Read the light sensor --
        lux = veml.lux
        print(f"Light: {lux:.1f} lux")

        # -- Connect to WiFi and send to Adafruit IO --
        if not wifi.radio.ipv4_address:
            wifi.radio.connect(
                getenv("CIRCUITPY_WIFI_SSID"),
                getenv("CIRCUITPY_WIFI_PASSWORD"),
            )
        print(f"WiFi connected - IP: {wifi.radio.ipv4_address}")

        pool = adafruit_connection_manager.get_radio_socketpool(wifi.radio)
        ssl_context = adafruit_connection_manager.get_radio_ssl_context(wifi.radio)
        requests = adafruit_requests.Session(pool, ssl_context)

        io = IO_HTTP(
            getenv("ADAFRUIT_AIO_USERNAME"),
            getenv("ADAFRUIT_AIO_KEY"),
            requests,
        )

        io.send_data(FEED_NAME, lux)
        print("Sent to Adafruit IO!")

    except Exception as e:
        print(f"ERROR: {e}")

    # -- Deep sleep (battery) or wait (USB) --
    print(f"Sleeping {SLEEP_INTERVAL} seconds...")
    time_alarm = alarm.time.TimeAlarm(
        monotonic_time=time.monotonic() + SLEEP_INTERVAL
    )
    alarm.exit_and_deep_sleep_until_alarms(time_alarm)
    # On battery: board resets, script runs from the top.
    # On USB: pretend sleep returns here, loop continues.
