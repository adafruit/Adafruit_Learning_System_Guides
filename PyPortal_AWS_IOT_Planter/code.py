"""
PyPortal Amazon AWS IoT Plant Monitor
=========================================================
Log your plant's vitals to AWS IoT and receive email
notifications when it needs watering with your PyPortal.

Author: Brent Rubell for Adafruit Industries, 2019
"""
import time
import json
import board
import busio
from digitalio import DigitalInOut
import neopixel
from adafruit_esp32spi import adafruit_esp32spi
from adafruit_esp32spi import adafruit_esp32spi_wifimanager
import adafruit_esp32spi.adafruit_esp32spi_socket as socket
import adafruit_minimqtt.adafruit_minimqtt as MQTT
from adafruit_aws_iot import MQTT_CLIENT
from adafruit_seesaw.seesaw import Seesaw
import aws_gfx_helper

# Time between polling the STEMMA, in minutes
SENSOR_DELAY = 15

# Get wifi details and more from a secrets.py file
try:
    from secrets import secrets
except ImportError:
    print("WiFi secrets are kept in secrets.py, please add them there!")
    raise

# Get device certificate
try:
    with open("aws_cert.pem.crt", "rb") as f:
        DEVICE_CERT = f.read()
except ImportError:
    print("Certificate (aws_cert.pem.crt) not found on CIRCUITPY filesystem.")
    raise

# Get device private key
try:
    with open("private.pem.key", "rb") as f:
        DEVICE_KEY = f.read()
except ImportError:
    print("Key (private.pem.key) not found on CIRCUITPY filesystem.")
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

# Verify nina-fw version >= 1.4.0
assert int(bytes(esp.firmware_version).decode("utf-8")[2]) >= 4, "Please update nina-fw to >=1.4.0."

status_light = neopixel.NeoPixel(board.NEOPIXEL, 1, brightness=0.2)
wifi = adafruit_esp32spi_wifimanager.ESPSPI_WiFiManager(
    esp, secrets, status_light)

# Initialize the graphics helper
print("Loading AWS IoT Graphics...")
gfx = aws_gfx_helper.AWS_GFX()
print("Graphics loaded!")

# Set AWS Device Certificate
esp.set_certificate(DEVICE_CERT)

# Set AWS RSA Private Key
esp.set_private_key(DEVICE_KEY)

# Connect to WiFi
print("Connecting to WiFi...")
wifi.connect()
print("Connected!")

# Initialize MQTT interface with the esp interface
MQTT.set_socket(socket, esp)

# Soil Sensor Setup
i2c_bus = busio.I2C(board.SCL, board.SDA)
ss = Seesaw(i2c_bus, addr=0x36)

# Define callback methods which are called when events occur
# pylint: disable=unused-argument, redefined-outer-name
def connect(client, userdata, flags, rc):
    # This function will be called when the client is connected
    # successfully to the broker.
    print('Connected to AWS IoT!')
    print('Flags: {0}\nRC: {1}'.format(flags, rc))

    # Subscribe client to all shadow updates
    print("Subscribing to shadow updates...")
    aws_iot.shadow_subscribe()

def disconnect(client, userdata, rc):
    # This method is called when the client disconnects
    # from the broker.
    print('Disconnected from AWS IoT!')

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
    print("Message from {}: {}".format(topic, msg))

# Set up a new MiniMQTT Client
client =  MQTT.MQTT(broker = secrets['broker'],
                    client_id = secrets['client_id'])

# Initialize AWS IoT MQTT API Client
aws_iot = MQTT_CLIENT(client)

# Connect callback handlers to AWS IoT MQTT Client
aws_iot.on_connect = connect
aws_iot.on_disconnect = disconnect
aws_iot.on_subscribe = subscribe
aws_iot.on_unsubscribe = unsubscribe
aws_iot.on_publish = publish
aws_iot.on_message = message

print('Attempting to connect to %s'%client.broker)
aws_iot.connect()

# Time in seconds since power on
initial = time.monotonic()

while True:
    try:
        gfx.show_aws_status('Listening for msgs...')
        now = time.monotonic()
        if now - initial > (SENSOR_DELAY * 60):
            # read moisture level
            moisture = ss.moisture_read()
            print("Moisture Level: ", moisture)
            # read temperature
            temperature = ss.get_temp()
            # Display Soil Sensor values on pyportal
            temperature = gfx.show_temp(temperature)
            gfx.show_water_level(moisture)
            print('Sending data to AWS IoT...')
            gfx.show_aws_status('Publishing data...')
            # Create a json-formatted device payload
            payload = {"state":{"reported":{"moisture":str(moisture),
                                            "temp":str(temperature)}}}
            # Update device shadow
            aws_iot.shadow_update(json.dumps(payload))
            gfx.show_aws_status('Data published!')
            print('Data sent!')
            # Reset timer
            initial = now
        aws_iot.loop()
    except (ValueError, RuntimeError) as e:
        print("Failed to get data, retrying", e)
        wifi.reset()
