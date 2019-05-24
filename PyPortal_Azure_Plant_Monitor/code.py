"""
PyPortal Azure IoT Plant Monitor
====================================================
Log plant vitals to Microsoft Azure IoT with
your PyPortal

Author: Brent Rubell for Adafruit Industries, 2019
"""
import time
import board
import busio
from digitalio import DigitalInOut
from adafruit_esp32spi import adafruit_esp32spi, adafruit_esp32spi_wifimanager
import neopixel
from adafruit_azureiot import IOT_Hub
from adafruit_seesaw.seesaw import Seesaw

# gfx helper
import azure_gfx_helper

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
status_light = neopixel.NeoPixel(board.NEOPIXEL, 1, brightness=0.2)
wifi = adafruit_esp32spi_wifimanager.ESPSPI_WiFiManager(esp, secrets, status_light)

# Soil Sensor Setup
i2c_bus = busio.I2C(board.SCL, board.SDA)
ss = Seesaw(i2c_bus, addr=0x36)

# Create an instance of the Azure IoT Hub
hub = IOT_Hub(wifi, secrets['azure_iot_hub'], secrets['azure_iot_sas'], secrets['azure_device_id'])

# init. graphics helper
gfx = azure_gfx_helper.Azure_GFX(False)

while True:
    try:
        # read moisture level
        moisture_level = ss.moisture_read()
        # read temperature
        temperature = ss.get_temp()
        # display soil sensor values on pyportal
        gfx.display_moisture(moisture_level)
        temperature = gfx.display_temp(temperature)
        print('Sending data to Azure')
        gfx.display_azure_status('Sending data...')
        hub.send_device_message(temperature)
        hub.send_device_message(moisture_level)
        gfx.display_azure_status('Data sent!')
        print('Data sent!')
    except (ValueError, RuntimeError) as e:
        print("Failed to get data, retrying\n", e)
        wifi.reset()
        continue
    time.sleep(60)
