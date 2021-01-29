"""
SHTC3 Temperature/Humidity Sensor Example for
using CircuitPython with Home Assistant

Author: Melissa LeBlanc-Williams for Adafruit Industries
"""

import time
import ssl
import json
import board
import busio
import socketpool
import wifi
import adafruit_minimqtt.adafruit_minimqtt as MQTT
import adafruit_shtc3

sht = adafruit_shtc3.SHTC3(busio.I2C(board.SCL, board.SDA))
PUBLISH_DELAY = 60
MQTT_TOPIC = "state/temp-sensor"

# Add a secrets.py to your filesystem that has a dictionary called secrets with "ssid" and
# "password" keys with your WiFi credentials. DO NOT share that file or commit it into Git or other
# source control.
# pylint: disable=no-name-in-module,wrong-import-order
try:
    from secrets import secrets
except ImportError:
    print("WiFi secrets are kept in secrets.py, please add them there!")
    raise

print("Connecting to %s" % secrets["ssid"])
wifi.radio.connect(secrets["ssid"], secrets["password"])
print("Connected to %s!" % secrets["ssid"])


### Secrets File Setup ###
try:
    from secrets import secrets
except ImportError:
    print("Connection secrets are kept in secrets.py, please add them there!")
    raise

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
    last_update = time.monotonic()

    # Pump the loop until we receive a message on `mqtt_topic`
    while time.monotonic() < last_update + PUBLISH_DELAY:
        mqtt_client.loop()

mqtt_client.disconnect()
