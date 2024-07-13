# SPDX-FileCopyrightText: 2024 johnpark for Adafruit Industries
#
# SPDX-License-Identifier: MIT
'''
BLE BBQ Thermometer to WiFi to Adafruit IO Dashboard
Feather ESP32-S3 8MB No PSRAM
'''
import os
import time
import adafruit_connection_manager
import wifi
import adafruit_minimqtt.adafruit_minimqtt as MQTT
import adafruit_ble
from adafruit_ble.advertising.standard import ProvideServicesAdvertisement
from adafruit_ble_ibbq import IBBQService


aio_username = os.getenv("aio_username")
aio_key = os.getenv("aio_key")

print(f"Connecting to {os.getenv('CIRCUITPY_WIFI_SSID')}")
wifi.radio.connect(
    os.getenv("CIRCUITPY_WIFI_SSID"), os.getenv("CIRCUITPY_WIFI_PASSWORD")
)
print(f"Connected to {os.getenv('CIRCUITPY_WIFI_SSID')}")

### Feeds ###
feeds = [aio_username + f"/feeds/bbq{i}" for i in range(1, 7)]
battery_feed = aio_username + "/feeds/bbq_battery"

# Define callback methods which are called when events occur
# pylint: disable=unused-argument, redefined-outer-name
def connected(client, userdata, flags, rc):
    print("Connected to Adafruit IO")

def disconnected(client, userdata, rc):
    print("Disconnected from Adafruit IO")

# Create a socket pool
pool = adafruit_connection_manager.get_radio_socketpool(wifi.radio)
ssl_context = adafruit_connection_manager.get_radio_ssl_context(wifi.radio)
connection_manager = adafruit_connection_manager.get_connection_manager(pool)

# Set up a MiniMQTT Client
mqtt_client = MQTT.MQTT(
    broker="io.adafruit.com",
    port=1883,
    username=aio_username,
    password=aio_key,
    socket_pool=pool,
    ssl_context=ssl_context,
)

# Setup the callback methods above
mqtt_client.on_connect = connected
mqtt_client.on_disconnect = disconnected

# Connect the client to the MQTT broker.
print("Connecting to Adafruit IO...")
mqtt_client.connect()

# PyLint can't find BLERadio for some reason so special case it here.
ble = adafruit_ble.BLERadio()  # pylint: disable=no-member

ibbq_connection = None
battery_percentage = 100

def c_to_f(temp_c):
    return (temp_c * 9/5) + 32

def volt_to_percent(voltage, max_voltage):
    return (voltage / max_voltage) * 100

def probe_check(temp):  # if value is wildly high no probe is connected
    return temp if temp <= 11000 else 0

battery_val = 3.3


while True:
    print("Scanning...")
    for adv in ble.start_scan(ProvideServicesAdvertisement, timeout=5):
        if IBBQService in adv.services:
            print("found an IBBq advertisement")
            ibbq_connection = ble.connect(adv)
            print("Connected")
            break

    # Stop scanning whether or not we are connected.
    ble.stop_scan()

    if ibbq_connection and ibbq_connection.connected:
        ibbq_service = ibbq_connection[IBBQService]
        ibbq_service.init()
        while ibbq_connection.connected:
            print(
                "Temperatures:",
                ibbq_service.temperatures,
                "; Battery:",
                ibbq_service.battery_level,
            )

            grill_vals = [probe_check(c_to_f(temp)) for temp in ibbq_service.temperatures]
            battery_val, battery_max = ibbq_service.battery_level
            battery_percentage = (volt_to_percent(battery_val, 3.3))

            mqtt_client.loop(timeout=1)

            for feed, val in zip(feeds, grill_vals):
                print(f"Sending grill value: {val} to {feed}...")
                mqtt_client.publish(feed, val)

            mqtt_client.publish(battery_feed, battery_percentage)
            print("Sent")
            time.sleep(5)
