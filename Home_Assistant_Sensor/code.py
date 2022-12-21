# SPDX-FileCopyrightText: 2021 Melissa LeBlanc-Williams for Adafruit Industries
#
# SPDX-License-Identifier: MIT

"""
SHTC3 Temperature/Humidity Sensor Example for
using CircuitPython with Home Assistant
Author: Melissa LeBlanc-Williams for Adafruit Industries
"""

import time
import ssl
import json
import alarm
import board
import socketpool
import wifi
import adafruit_minimqtt.adafruit_minimqtt as MQTT
import adafruit_shtc3

PUBLISH_DELAY = 60
MQTT_TOPIC = "state/temp-sensor"
USE_DEEP_SLEEP = True

# Connect to the Sensor
i2c = board.I2C()  # uses board.SCL and board.SDA
# i2c = board.STEMMA_I2C()  # For using the built-in STEMMA QT connector on a microcontroller
sht = adafruit_shtc3.SHTC3(i2c)

# Add a secrets.py to your filesystem that has a dictionary called secrets with "ssid" and
# "password" keys with your WiFi credentials. DO NOT share that file or commit it into Git or other
# source control.
# pylint: disable=no-name-in-module,wrong-import-order
try:
    from secrets import secrets
except ImportError:
    print("WiFi secrets are kept in secrets.py, please add them there!")
    raise

wifi.radio.connect(secrets["ssid"], secrets["password"])
print("Connected to %s!" % secrets["ssid"])

# Create a socket pool
pool = socketpool.SocketPool(wifi.radio)

# Set up a MiniMQTT Client
mqtt_client = MQTT.MQTT(
    broker=secrets["mqtt_broker"],
    port=secrets["mqtt_port"],
    username=secrets["mqtt_username"],
    password=secrets["mqtt_password"],
    socket_pool=pool,
    ssl_context=ssl.create_default_context(),
)

print("Attempting to connect to %s" % mqtt_client.broker)
mqtt_client.connect()

while True:
    temperature, relative_humidity = sht.measurements

    output = {
        "temperature": temperature,
        "humidity": relative_humidity,
    }

    print("Publishing to %s" % MQTT_TOPIC)
    mqtt_client.publish(MQTT_TOPIC, json.dumps(output))

    if USE_DEEP_SLEEP:
        mqtt_client.disconnect()
        pause = alarm.time.TimeAlarm(monotonic_time=time.monotonic() + PUBLISH_DELAY)
        alarm.exit_and_deep_sleep_until_alarms(pause)
    else:
        last_update = time.monotonic()
        while time.monotonic() < last_update + PUBLISH_DELAY:
            mqtt_client.loop()
