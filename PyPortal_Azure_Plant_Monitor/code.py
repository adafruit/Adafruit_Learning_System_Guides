"""
PyPortal Azure IoT Plant Monitor
====================================================
Log plant vitals to Microsoft Azure IoT Central with
your PyPortal

Authors: Brent Rubell for Adafruit Industries, 2019
       : Jim Bennett for Microsoft, 2020
"""
import time
import json
import board
import busio
from digitalio import DigitalInOut
from adafruit_esp32spi import adafruit_esp32spi, adafruit_esp32spi_wifimanager
import adafruit_esp32spi.adafruit_esp32spi_socket as socket
import neopixel
from adafruit_ntp import NTP
from adafruit_azureiot import IoTCentralDevice
from adafruit_seesaw.seesaw import Seesaw

# gfx helper
import azure_gfx_helper

# init. graphics helper
gfx = azure_gfx_helper.Azure_GFX(is_celsius=True)

# Get wifi details and more from a secrets.py file
try:
    from secrets import secrets
except ImportError:
    print("WiFi secrets are kept in secrets.py, please add them there!")
    raise

# PyPortal ESP32 Setup
esp32_cs = DigitalInOut(board.ESP_CS)
esp32_ready = DigitalInOut(board.ESP_BUSY)
esp32_reset = DigitalInOut(board.ESP_RESET)
spi = busio.SPI(board.SCK, board.MOSI, board.MISO)
esp = adafruit_esp32spi.ESP_SPIcontrol(spi, esp32_cs, esp32_ready, esp32_reset)

# Set up the WiFi manager with a status light to show the WiFi connection status
status_light = neopixel.NeoPixel(board.NEOPIXEL, 1, brightness=0.2)
wifi = adafruit_esp32spi_wifimanager.ESPSPI_WiFiManager(esp, secrets, status_light)
print("WiFi connecting...")
wifi.connect()
print("WiFi connected!")

# Time setup, needed to authenticate with Azure IoT Central
ntp = NTP(esp)
while not ntp.valid_time:
    print("Failed to obtain time, retrying in 5 seconds...")
    time.sleep(5)
    ntp.set_time()

# Soil Sensor Setup
i2c_bus = busio.I2C(board.SCL, board.SDA)
ss = Seesaw(i2c_bus, addr=0x36)

# Create an instance of the Azure IoT Central device
device = IoTCentralDevice(
    socket,
    esp,
    secrets["id_scope"],
    secrets["device_id"],
    secrets["key"]
)

# Connect to Azure IoT Central
device.connect()

# Hide the splash screen and show the telemetry values
gfx.show_text()

while True:
    try:
        # read moisture level
        moisture_level = ss.moisture_read()
        # read temperature
        temperature = ss.get_temp()
        # display soil sensor values on pyportal
        gfx.display_moisture(moisture_level)
        gfx.display_temp(temperature)

        print('Sending data to Azure')
        gfx.display_azure_status('Sending data...')

        # send the temperature and moisture level to Azure
        message = {
            "Temperature": temperature,
            "MoistureLevel": moisture_level
        }
        device.send_telemetry(json.dumps(message))
        device.loop()

        gfx.display_azure_status('Data sent!')
        print('Data sent!')
    except (ValueError, RuntimeError) as e:
        print("Failed to get data, retrying\n", e)
        wifi.reset()
        wifi.connect()
        device.reconnect()
        continue

    # Sleep for 10 minutes before getting the next value
    time.sleep(600)
