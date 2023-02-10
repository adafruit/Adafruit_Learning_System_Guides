# SPDX-FileCopyrightText: 2023 Trevor Beaton for Adafruit Industries
#
# SPDX-License-Identifier: MIT
import time
import ssl
import math
import board
import microcontroller
import wifi
import socketpool
import adafruit_minimqtt.adafruit_minimqtt as MQTT
from adafruit_io.adafruit_io import IO_MQTT
from adafruit_adxl34x import ADXL345
from adafruit_lc709203f import LC709203F, PackSize

try:
    from secrets import secrets
except ImportError:
    print("Adafruit IO credentials are kept in secrets.py - please add them there!")
    raise

aio_username = secrets["aio_username"]
aio_key = secrets["aio_key"]

# Create a socket pool
pool = socketpool.SocketPool(wifi.radio)

# Initialize a new MQTT Client object
mqtt_client = MQTT.MQTT(
    broker="io.adafruit.com",
    username=secrets["aio_username"],
    password=secrets["aio_key"],
    socket_pool=pool,
    ssl_context=ssl.create_default_context(),
)

# Initialize Adafruit IO MQTT "helper"
io = IO_MQTT(mqtt_client)

try:
    # If Adafruit IO is not connected...
    if not io.is_connected:
    # Connect the client to the MQTT broker.
        print("Connecting to Adafruit IO...")
        io.connect()
        print("Connected to Adafruit IO!")
except Exception as e:  # pylint: disable=broad-except
    print("Failed to get or send data, or connect. Error:", e,
    "\nBoard will hard reset in 30 seconds.")
    time.sleep(30)
    microcontroller.reset()

threshold = 20 # set threshold value here
time_interval = 0.5 # set the time interval in seconds

# create the I2C bus object
i2c = board.STEMMA_I2C()
# For ADXL345
accelerometer = ADXL345(i2c)

battery_monitor = LC709203F(i2c)
battery_monitor.pack_size = PackSize.MAH400

t0 = time.monotonic()

while True:
    x, y, z = accelerometer.acceleration
    t1 = time.monotonic()
    dt = t1 - t0

    total_acceleration = math.sqrt(x**2 + y**2 + z**2)
    if total_acceleration >= threshold:
        print("Battery Percent: {:.2f} %".format(battery_monitor.cell_percent))
        print("Collision strength: %.2f" % total_acceleration)
        io.publish("punch-strength", total_acceleration)

        # add code here to trigger an event or alert the user
    t0 = t1
    time.sleep(time_interval)
