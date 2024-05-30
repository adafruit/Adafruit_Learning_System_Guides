# SPDX-FileCopyrightText: 2024 Liz Clark for Adafruit Industries
#
# SPDX-License-Identifier: MIT

import time
import serial
from Adafruit_IO import MQTTClient

# Configuration
com_port = 'COM123'  # Adjust this to your COM port
baud_rate = 115200
FEED_ID = 'pixel-feed'
# Set to your Adafruit IO key.
# Remember, your key is a secret,
# so make sure not to publish it when you publish this code!
ADAFRUIT_IO_KEY = 'your-aio-key'

# Set to your Adafruit IO username.
# (go to https://accounts.adafruit.com to find your username)
ADAFRUIT_IO_USERNAME = 'your-aio-username'

print("Connecting to Adafruit IO...")

# Initialize the serial connection
ser = serial.Serial(com_port, baud_rate)

# Define callback functions
def connected(client):
    client.subscribe(FEED_ID)
# pylint: disable=unused-argument, consider-using-sys-exit
def subscribe(client, userdata, mid, granted_qos):
    # This method is called when the client subscribes to a new feed.
    print(f"Subscribed to {FEED_ID}")

def disconnected(client):
    print('Disconnected from Adafruit IO!')
    exit(1)

def message(client, feed_id, payload):
    print(f'Feed {feed_id} received new value: {payload}')
    color_value = payload.strip().replace('#', '0x')  # Replace # with 0x
    ser.write(color_value.encode())  # Send the color value to the serial port

# Initialize the Adafruit IO MQTT client
mqtt_client = MQTTClient(ADAFRUIT_IO_USERNAME, ADAFRUIT_IO_KEY)

# Setup the callback functions
mqtt_client.on_connect = connected
mqtt_client.on_disconnect = disconnected
mqtt_client.on_message = message
mqtt_client.on_subscribe  = subscribe

# Connect to Adafruit IO
mqtt_client.connect()

# Start a background thread to listen for MQTT messages
mqtt_client.loop_blocking()

# Keep the script running
while True:
    try:
        time.sleep(1)
    except KeyboardInterrupt:
        print('Script interrupted by user')
        break

# Close the serial connection when done
ser.close()
