"""
PyPortal Google Cloud IoT Core Planter
=======================================================
Water your plant remotely and log its vitals to Google
Cloud IoT Core with your PyPortal.

Author: Brent Rubell for Adafruit Industries, 2019
"""
import time
import json
import board
import busio
import gcp_gfx_helper
import neopixel
from adafruit_esp32spi import adafruit_esp32spi, adafruit_esp32spi_wifimanager
import adafruit_esp32spi.adafruit_esp32spi_socket as socket
from adafruit_gc_iot_core import MQTT_API, Cloud_Core
import adafruit_minimqtt.adafruit_minimqtt as MQTT
from adafruit_seesaw.seesaw import Seesaw
import digitalio

# Delay before reading the sensors, in minutes
SENSOR_DELAY = 10

# Get wifi details and more from a secrets.py file
try:
    from secrets import secrets
except ImportError:
    print("WiFi secrets are kept in secrets.py, please add them there!")
    raise

# PyPortal ESP32 Setup
esp32_cs = digitalio.DigitalInOut(board.ESP_CS)
esp32_ready = digitalio.DigitalInOut(board.ESP_BUSY)
esp32_reset = digitalio.DigitalInOut(board.ESP_RESET)
spi = busio.SPI(board.SCK, board.MOSI, board.MISO)
esp = adafruit_esp32spi.ESP_SPIcontrol(spi, esp32_cs, esp32_ready, esp32_reset)
status_light = neopixel.NeoPixel(board.NEOPIXEL, 1, brightness=0.2)
wifi = adafruit_esp32spi_wifimanager.ESPSPI_WiFiManager(
    esp, secrets, status_light)

# Connect to WiFi
print("Connecting to WiFi...")
wifi.connect()
print("Connected!")

# Initialize MQTT interface with the esp interface
MQTT.set_socket(socket, esp)

# Soil Sensor Setup
i2c_bus = busio.I2C(board.SCL, board.SDA)
ss = Seesaw(i2c_bus, addr=0x36)

# Water Pump Setup
water_pump = digitalio.DigitalInOut(board.D3)
water_pump.direction = digitalio.Direction.OUTPUT

# Initialize the graphics helper
print("Loading GCP Graphics...")
gfx = gcp_gfx_helper.Google_GFX()
print("Graphics loaded!")


# Define callback methods which are called when events occur
# pylint: disable=unused-argument, redefined-outer-name
def connect(client, userdata, flags, rc):
    # This function will be called when the client is connected
    # successfully to the broker.
    print('Connected to Google Cloud IoT!')
    print('Flags: {0}\nRC: {1}'.format(flags, rc))
    # Subscribes to commands/# topic
    google_mqtt.subscribe_to_all_commands()


def disconnect(client, userdata, rc):
    # This method is called when the client disconnects
    # from the broker.
    print('Disconnected from Google Cloud IoT!')


def subscribe(client, userdata, topic, granted_qos):
    # This method is called when the client subscribes to a new topic.
    print('Subscribed to {0} with QOS level {1}'.format(topic, granted_qos))


def unsubscribe(client, userdata, topic, pid):
    # This method is called when the client unsubscribes from a topic.
    print('Unsubscribed from {0} with PID {1}'.format(topic, pid))


def publish(client, userdata, topic, pid):
    # This method is called when the client publishes data to a topic.
    print('Published to {0} with PID {1}'.format(topic, pid))


def message(client, topic, msg):
    # This method is called when the client receives data from a topic.
    try:
        # Attempt to decode a JSON command
        msg_dict = json.loads(msg)
        # Handle water-pump commands
        if msg_dict['pump_time']:
            handle_pump(msg_dict)
    except TypeError:
        # Non-JSON command, print normally
        print("Message from {}: {}".format(topic, msg))


def handle_pump(command):
    """Handles command about the planter's
    watering pump from Google Core IoT.
    :param json command: Message from device/commands#
    """
    print("handling pump...")
    # Parse the pump command message
    # Expected format: {"power": true, "pump_time":3}
    pump_time = command['pump_time']
    pump_status = command['power']
    if pump_status:
        print("Turning pump on for {} seconds...".format(pump_time))
        start_pump = time.monotonic()
        while True:
            gfx.show_gcp_status('Watering plant...')
            cur_time = time.monotonic()
            if cur_time - start_pump > pump_time:
                # Timer expired, leave the loop
                print("Plant watered!")
                break
            water_pump.value = True
    gfx.show_gcp_status('Plant watered!')
    print("Turning pump off")
    water_pump.value = False


# Initialize Google Cloud IoT Core interface
google_iot = Cloud_Core(esp, secrets)

# JSON-Web-Token (JWT) Generation
print("Generating JWT...")
jwt = google_iot.generate_jwt()
print("Your JWT is: ", jwt)

# Set up a new MiniMQTT Client
client = MQTT.MQTT(broker=google_iot.broker,
                   username=google_iot.username,
                   password=jwt,
                   client_id=google_iot.cid)

# Initialize Google MQTT API Client
google_mqtt = MQTT_API(client)

# Connect callback handlers to Google MQTT Client
google_mqtt.on_connect = connect
google_mqtt.on_disconnect = disconnect
google_mqtt.on_subscribe = subscribe
google_mqtt.on_unsubscribe = unsubscribe
google_mqtt.on_publish = publish
google_mqtt.on_message = message

print('Attempting to connect to %s' % client.broker)
google_mqtt.connect()

# Time in seconds since power on
initial = time.monotonic()

while True:
    try:
        gfx.show_gcp_status('Listening for new messages...')
        now = time.monotonic()
        if now - initial > (SENSOR_DELAY * 60):
            # read moisture level
            moisture_level = ss.moisture_read()
            # read temperature
            temperature = ss.get_temp()
            # Display Soil Sensor values on pyportal
            temperature = gfx.show_temp(temperature)
            gfx.show_water_level(moisture_level)
            print('Sending data to GCP IoT Core')
            gfx.show_gcp_status('Publishing data...')
            google_mqtt.publish(temperature, "events")
            time.sleep(2)
            google_mqtt.publish(moisture_level, "events")
            gfx.show_gcp_status('Data published!')
            print('Data sent!')
            # Reset timer
            initial = now
        google_mqtt.loop()
    except (ValueError, RuntimeError) as e:
        print("Failed to get data, retrying", e)
        wifi.reset()
        google_mqtt.reconnect()
        continue
