# SPDX-FileCopyrightText: Copyright (c) 2024 Trevor Beaton for Adafruit Industries
# SPDX-License-Identifier: MIT

import os
import time
import ssl
import binascii
import gc
import wifi
import socketpool
import adafruit_requests
import adafruit_minimqtt.adafruit_minimqtt as MQTT
from adafruit_io.adafruit_io import IO_HTTP, AdafruitIO_RequestError
import adafruit_pycamera

# WiFi and Adafruit IO setup
aio_username = os.getenv("AIO_USERNAME")
aio_key = os.getenv("AIO_KEY")

print(f"Connecting to {os.getenv('CIRCUITPY_WIFI_SSID')}")
wifi.radio.connect(
    os.getenv("CIRCUITPY_WIFI_SSID"), os.getenv("CIRCUITPY_WIFI_PASSWORD")
)
print(f"Connected to {os.getenv('CIRCUITPY_WIFI_SSID')}!")

mqtt_broker = "io.adafruit.com"
mqtt_port = 1883
mqtt_topic = aio_username + "/feeds/cameratrigger"

pool = socketpool.SocketPool(wifi.radio)
requests = adafruit_requests.Session(pool, ssl.create_default_context())

# Initialize an Adafruit IO HTTP API object
io = IO_HTTP(aio_username, aio_key, requests)

# Adafruit IO feed configuration
try:
    feed_camera = io.get_feed("camera")
except AdafruitIO_RequestError:
    feed_camera = io.create_new_feed("camera")

# Initialize memento camera
pycam = adafruit_pycamera.PyCamera()
time.sleep(2)  #

# Camera settings
pycam.mode = 0
pycam.resolution = 3
pycam.led_level = 1
pycam.led_color = 0
pycam.effect = 0

def cameraChime():
    notes = [
        (1046, 0.1),  # C6
        (1318, 0.1),  # E6
        (1568, 0.4),  # G6
    ]
    for frequency, duration in notes:
        pycam.tone(frequency, duration)
        time.sleep(0.05)

cameraChime()

def on_mqtt_connect(client, _, __, ___):
    print(f"Connected to MQTT broker! Listening for topic changes on {mqtt_topic}")
    client.subscribe(mqtt_topic)

def on_mqtt_disconnect(_, __, ___):
    print("Disconnected from MQTT broker!")

def on_mqtt_message(_, topic, message):
    print(f"New message on topic {topic}: {message}")
    cameraChime()
    capture_send_image()

# Set up MQTT client
ssl_context = ssl.create_default_context()
mqtt_client = MQTT.MQTT(
    broker=mqtt_broker,
    port=mqtt_port,
    username=aio_username,
    password=aio_key,
    socket_pool=pool,
    ssl_context=ssl_context,
    socket_timeout=5,
    keep_alive=60
)
# Set up callbacks
mqtt_client.on_connect = on_mqtt_connect
mqtt_client.on_disconnect = on_mqtt_disconnect
mqtt_client.on_message = on_mqtt_message


# Connect to MQTT broker
print("Connecting to MQTT broker...")
mqtt_client.connect()

def capture_send_image():
    """Captures an image and sends it to Adafruit IO."""
    gc.collect()  # Free up memory before capture
    try:
        pycam.autofocus()
        time.sleep(1)  # Add a small delay after autofocus
        jpeg = pycam.capture_into_jpeg()
        print("Captured image!")
        if jpeg is not None:
            print("Encoding image...")
            encoded_data = binascii.b2a_base64(jpeg).strip()
            print("Sending image to Adafruit IO...")
            io.send_data(feed_camera["key"], encoded_data)
            print("Sent image to IO!")
            cameraChime()
        else:
            print("ERROR: JPEG frame capture failed!")
    except (OSError, RuntimeError) as capture_error:
        print(f"Error during capture: {capture_error}")

last_mqtt_check = 0
MQTT_CHECK_INTERVAL = 1  # Check MQTT every 1 second

while True:
    try:
        current_time = time.monotonic()

        # Check MQTT messages periodically
        if current_time - last_mqtt_check >= MQTT_CHECK_INTERVAL:
            mqtt_client.loop(timeout=6)
            last_mqtt_check = current_time

        pycam.keys_debounce()
        if pycam.shutter.short_count:
            print("Manual capture triggered")
            capture_send_image()

        time.sleep(0.1)
    except MQTT.MMQTTException as mqtt_error:
        print(f"MQTT Error: {mqtt_error}")
        time.sleep(5)
        print("Attempting to reconnect...")
        try:
            mqtt_client.reconnect()
            print("Reconnected successfully!")
        except (OSError, RuntimeError) as reconnect_error:
            print(f"Failed to reconnect: {reconnect_error}")
    except (OSError, RuntimeError) as loop_error:
        print(f"Error in main loop: {loop_error}")
        time.sleep(5)
