# SPDX-FileCopyrightText: 2021 Dylan Herrada for Adafruit Industries
# SPDX-License-Identifier: MIT

import ssl
import time
import board
import digitalio
import socketpool
import wifi
import adafruit_minimqtt.adafruit_minimqtt as MQTT
from adafruit_io.adafruit_io import IO_MQTT

led = digitalio.DigitalInOut(board.IO8)
led.direction = digitalio.Direction.OUTPUT

btn1 = digitalio.DigitalInOut(board.IO9)
btn1.direction = digitalio.Direction.INPUT
btn1.pull = digitalio.Pull.DOWN

ALARM = None
### WiFi ###

# Get wifi details and more from a secrets.py file
try:
    from secrets import secrets
except ImportError:
    print("WiFi secrets are kept in secrets.py, please add them there!")
    raise

print("Connecting to %s" % secrets["ssid"])
wifi.radio.connect(secrets["ssid"], secrets["password"])
print("Connected to %s!" % secrets["ssid"])

# Define callback functions which will be called when certain events happen.
# pylint: disable=unused-argument
def connected(client):
    # Connected function will be called when the client is connected to Adafruit IO.
    # This is a good place to subscribe to feed changes.  The client parameter
    # passed to this function is the Adafruit IO MQTT client so you can make
    # calls against it easily.
    print("Connected to Adafruit IO!")
    client.subscribe("alarm-clock.alarm")


def subscribe(client, userdata, topic, granted_qos):
    # This method is called when the client subscribes to a new feed.
    print("Subscribed to {0} with QOS level {1}".format(topic, granted_qos))


def unsubscribe(client, userdata, topic, pid):
    # This method is called when the client unsubscribes from a feed.
    print("Unsubscribed from {0} with PID {1}".format(topic, pid))


# pylint: disable=unused-argument
def disconnected(client):
    # Disconnected function will be called when the client disconnects.
    print("Disconnected from Adafruit IO!")


# pylint: disable=unused-argument
def message(client, feed_id, payload):
    # Message function will be called when a subscribed feed has a new value.
    # The feed_id parameter identifies the feed, and the payload parameter has
    # the new value.
    print("Feed {0} received new value: {1}".format(feed_id, payload))


def on_alarm(client, feed_id, payload):
    global ALARM # pylint: disable=global-statement
    print(payload)
    ALARM = eval(payload) # pylint: disable=eval-used


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

# Initialize an Adafruit IO MQTT Client
io = IO_MQTT(mqtt_client)

# Connect the callback methods defined above to Adafruit IO
io.on_connect = connected
io.on_disconnect = disconnected
io.on_subscribe = subscribe
io.on_unsubscribe = unsubscribe
io.on_message = message

io.add_feed_callback("alarm-clock.alarm", on_alarm)

# Connect to Adafruit IO
print("Connecting to Adafruit IO...")
io.connect()

io.get("alarm-clock.alarm")

LAST = 0
while True:
    io.loop()
    if ALARM and time.monotonic() - LAST >= 0.2:
        led.value = not led.value
        LAST = time.monotonic()
    if btn1.value:
        io.publish("alarm-clock.alarm", "False")
        led.value = False
        led.value = True
        time.sleep(1)
        led.value = False
