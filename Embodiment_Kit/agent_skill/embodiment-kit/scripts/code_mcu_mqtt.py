# SPDX-FileCopyrightText: 2026 Tim Cocks for Adafruit Industries
# SPDX-License-Identifier: MIT
import json
from os import getenv

import board
import audiobusio
import digitalio
import pwmio
import supervisor
import wifi
import socketpool
import rtc

from adafruit_bme280 import basic as adafruit_bme280
from adafruit_io.adafruit_io import IO_MQTT
import adafruit_ntp
from adafruit_debouncer import Debouncer
from embodiment_message_handler import EmbodimentMessageHandler
import adafruit_veml7700
import adafruit_lis3dh
import adafruit_drv2605
import adafruit_connection_manager
import adafruit_minimqtt.adafruit_minimqtt as MQTT
import neopixel

# Get WiFi details and Adafruit IO keys, ensure these are setup in settings.toml
# (visit io.adafruit.com if you need to create an account, or if you need your Adafruit IO key.)
ssid = getenv("CIRCUITPY_WIFI_SSID")
password = getenv("CIRCUITPY_WIFI_PASSWORD")
aio_username = getenv("ADAFRUIT_AIO_USERNAME")
aio_key = getenv("ADAFRUIT_AIO_KEY")

### WiFi ###
if not wifi.radio.connected:
    print(f"Connecting to {ssid}")
    wifi.radio.connect(ssid, password)
    print(f"Connected to {ssid}!")

# update system time
pool = socketpool.SocketPool(wifi.radio)
ntp = adafruit_ntp.NTP(pool, tz_offset=0, cache_seconds=3600)
cur_time = rtc.RTC()
cur_time.datetime = ntp.datetime

### Initialize hardware components ###
bme280 = adafruit_bme280.Adafruit_BME280_I2C(board.I2C())
veml7700 = adafruit_veml7700.VEML7700(board.I2C())
mic = audiobusio.PDMIn(board.D6, board.D5, sample_rate=16000, bit_depth=16)
buzzer = pwmio.PWMOut(board.D9, variable_frequency=True)

lis3dh = adafruit_lis3dh.LIS3DH_I2C(board.I2C())
lis3dh.data_rate = adafruit_lis3dh.DATARATE_1344_HZ

rgb_strip = neopixel.NeoPixel(board.D10, 8, brightness=0.3, auto_write=True)

drv = adafruit_drv2605.DRV2605(board.I2C())
drv.sequence[0] = adafruit_drv2605.Effect(15)  # Set the effect on slot 0.

embodiment_config = {
    "sensors": [
        {"type": "temperature", "sensor": bme280, "units": "C"},
        {"type": "pressure", "sensor": bme280, "units": "hPa"},
        {"type": "humidity", "sensor": bme280, "units": "%"},
        {"type": "lux", "sensor": veml7700, "units": "lux", "property": "autolux"},
        {"type": "pdm_mic", "sensor": mic, "units": "normalized_rms"},
        {
            "type": "accelerometer",
            "sensor": lis3dh,
            "units": "G",
        },
    ],
    "buttons": {},
    "piezo_buzzer": buzzer,
    "vibration_driver": drv,
    "neopixels": rgb_strip,
    "display": supervisor.runtime.display,
}

pins = [(board.D0, "D0"), (board.D1, "D1"), (board.D2, "D2")]
for pin_i in range(len(pins)):
    pin = pins[pin_i]
    dio = digitalio.DigitalInOut(pin[0])
    dio.direction = digitalio.Direction.INPUT
    # Pins D1 and D2 use different PULL from pin D0
    if pin_i == 0:
        dio.pull = digitalio.Pull.UP
    else:
        dio.pull = digitalio.Pull.DOWN
    btn = Debouncer(dio)
    embodiment_config["buttons"][pin[1]] = btn

embodiment_message_handler = EmbodimentMessageHandler(embodiment_config)

display = supervisor.runtime.display
display.root_group = embodiment_message_handler.main_group


# Define callback functions for MQTT
def connected(client):
    print(
        "Connected to Adafruit IO!  Listening for embodiment.client-to-mcu messages..."
    )
    # Subscribe to changes on a feed named embodiment.client-to-mcu.
    client.subscribe("embodiment.client-to-mcu")


def subscribe(_, __, topic, granted_qos):
    # This method is called when the client subscribes to a new feed.
    print(f"Subscribed to {topic} with QOS level {granted_qos}")


def unsubscribe(_, __, topic, pid):
    # This method is called when the client unsubscribes from a feed.
    print(f"Unsubscribed from {topic} with PID {pid}")


def disconnected(_):
    # Disconnected function will be called when the client disconnects.
    print("Disconnected from Adafruit IO!")


def publish(_, userdata, topic, pid):
    # This method is called when the client publishes data to a feed.
    print(f"Published to {topic} with PID {pid}. userdata is None ? {userdata is None}")
    if userdata is not None:
        print("Published User data: ", end="")
        print(userdata)


def message(_, feed_id, payload):
    print(f"Feed {feed_id} received new value: {payload}")
    data = json.loads(payload)
    if "messages" in data:
        resp_obj = embodiment_message_handler.handle_messages(data["messages"])
        io.publish("embodiment.mcu-to-client", json.dumps(resp_obj))


# Create a socket pool and ssl_context
pool = adafruit_connection_manager.get_radio_socketpool(wifi.radio)
ssl_context = adafruit_connection_manager.get_radio_ssl_context(wifi.radio)

# Initialize a new MQTT Client object
mqtt_client = MQTT.MQTT(
    broker="io.adafruit.com",
    port=8883,
    username=aio_username,
    password=aio_key,
    socket_pool=pool,
    ssl_context=ssl_context,
    is_ssl=True,
)

# Initialize an Adafruit IO MQTT Client
io = IO_MQTT(mqtt_client, feed_history_enabled=False)

# Connect the callback methods defined above to Adafruit IO
io.on_connect = connected
io.on_disconnect = disconnected
io.on_subscribe = subscribe
io.on_unsubscribe = unsubscribe
io.on_message = message
io.on_publish = publish

print("Connecting to Adafruit IO...")
io.connect()

# Increase message size limit for history disabled feed
io._client.mqtt_msg = 1024 * 100  # pylint: disable=protected-access

while True:
    io.loop()
