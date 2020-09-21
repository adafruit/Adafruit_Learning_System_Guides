import time
import board
import busio
from digitalio import DigitalInOut
import neopixel
import adafruit_bh1750
from adafruit_esp32spi import adafruit_esp32spi
from adafruit_esp32spi import adafruit_esp32spi_wifimanager
import adafruit_esp32spi.adafruit_esp32spi_socket as socket

import adafruit_minimqtt.adafruit_minimqtt as MQTT

### Sensor Calibration ###

APPLIANCE_ON_LUX = 30.0
APPLIANCE_OFF_LUX = 4.0
# How often the light sensor will be read, in seconds
SENSOR_READ_TIME = 5.0

### WiFi ###

# Get wifi details and more from a secrets.py file
try:
    from secrets import secrets
except ImportError:
    print("WiFi secrets are kept in secrets.py, please add them there!")
    raise

# If you are using a board with pre-defined ESP32 Pins:
esp32_cs = DigitalInOut(board.ESP_CS)
esp32_ready = DigitalInOut(board.ESP_BUSY)
esp32_reset = DigitalInOut(board.ESP_RESET)

# If you have an externally connected ESP32:
# esp32_cs = DigitalInOut(board.D9)
# esp32_ready = DigitalInOut(board.D10)
# esp32_reset = DigitalInOut(board.D5)

spi = busio.SPI(board.SCK, board.MOSI, board.MISO)
esp = adafruit_esp32spi.ESP_SPIcontrol(spi, esp32_cs, esp32_ready, esp32_reset)
"""Use below for Most Boards"""
status_light = neopixel.NeoPixel(
    board.NEOPIXEL, 1, brightness=0.2
)  # Uncomment for Most Boards
"""Uncomment below for ItsyBitsy M4"""
# status_light = dotstar.DotStar(board.APA102_SCK, board.APA102_MOSI, 1, brightness=0.2)
# Uncomment below for an externally defined RGB LED
# import adafruit_rgbled
# from adafruit_esp32spi import PWMOut
# RED_LED = PWMOut.PWMOut(esp, 26)
# GREEN_LED = PWMOut.PWMOut(esp, 27)
# BLUE_LED = PWMOut.PWMOut(esp, 25)
# status_light = adafruit_rgbled.RGBLED(RED_LED, BLUE_LED, GREEN_LED)
wifi = adafruit_esp32spi_wifimanager.ESPSPI_WiFiManager(esp, secrets, status_light)

# Set up a pin for controlling the relay
power_pin = DigitalInOut(board.D3)
power_pin.switch_to_output()

# Set up the light sensor
i2c = board.I2C()
sensor = adafruit_bh1750.BH1750(i2c)

### Feeds ###
# Set up a feed named Relay for subscribing to the relay feed on Adafruit IO
feed_relay = secrets["aio_username"] + "/feeds/relay"

# Set up a feed named status for subscribing to the status feed on Adafruit IO
feed_status = secrets["aio_username"] + "/feeds/status"

### Code ###

# Define callback methods which are called when events occur
# pylint: disable=unused-argument, redefined-outer-name
def connected(client, userdata, flags, rc):
    # This function will be called when the client is connected
    # successfully to the broker.
    print("Connected to Adafruit IO!")


def disconnected(client, userdata, rc):
    # This method is called when the client is disconnected
    print("Disconnected from Adafruit IO!")


def subscribe(client, userdata, topic, granted_qos):
    # This method is called when the client subscribes to a new feed.
    print("Subscribed to {0}".format(topic))


def unsubscribe(client, userdata, topic, pid):
    # This method is called when the client unsubscribes from a feed.
    print("Unsubscribed from {0} with PID {1}".format(topic, pid))

def on_message(client, topic, message):
    # Method callled when a client's subscribed feed has a new value.
    print("New message on topic {0}: {1}".format(topic, message))


def on_relay_msg(client, topic, value):
    # Called when relay feed obtains a new value
    print("Turning Relay %s"%value)
    if value == "ON":
        power_pin.value = True
    elif value == "OFF":
        power_pin.value = False
    else:
        print("Unexpected value received on relay feed.")

# Connect to WiFi
print("Connecting to WiFi...")
wifi.connect()
print("Connected!")

MQTT.set_socket(socket, esp)

# Set up a MiniMQTT Client
client = MQTT.MQTT(
    broker="io.adafruit.com",
    username=secrets["aio_username"],
    password=secrets["aio_key"],
)

# Setup the callback methods above
client.on_connect = connected
client.on_disconnect = disconnected
client.on_subscribe = subscribe
client.on_unsubscribe = unsubscribe
client.on_message = on_message
# Add a callback to the relay feed
client.add_topic_callback(feed_relay, on_relay_msg)

# Connect the client to Adafruit IO
print("Connecting to Adafruit IO...")
client.connect()

# Subscribe to all updates on relay feed
client.subscribe(feed_relay)

# Holds state of light sensor
prv_sensor_value = 0
# Time in seconds since start
start_time = time.monotonic()

while True:
    try:
        # Poll for new messages on feed_relay
        client.loop()
        now = time.monotonic()
        if now - start_time > 3.0:
            # Read light sensor
            print("Reading light sensor")
            sensor_value = sensor.lux
            print("%.2f Lux" % sensor.lux)
            if sensor_value != prv_sensor_value:
                # Light sensor value changed between readings
                if sensor_value > APPLIANCE_ON_LUX:
                    # Appliance is ON, publish to feed_status
                    print("Appliance ON, publishing to IO...")
                    client.publish(feed_status, 1)
                    print("Published!")
                else:
                    # Appliance is OFF, publish to feed_status
                    print("Appliance OFF, publishing to IO...")
                    client.publish(feed_status, 2)
                    print("Published!")
            start_time = now
    except (ValueError, RuntimeError) as e:
        print("Failed to get data, retrying\n", e)
        wifi.reset()
        client.reconnect()
        continue
    time.sleep(0.5)
