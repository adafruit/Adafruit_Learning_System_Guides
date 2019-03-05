"""
PyPortal Weather Station
==============================================
Turn your PyPortal into a weaterstation with
Adafruit IO

Author: Brent Rubell for Adafruit Industries, 2019

Dependencies:
    TODO: List all deps!
"""
import time
import board
import neopixel
import busio
import analogio
from simpleio import map_range
from digitalio import DigitalInOut

from adafruit_esp32spi import adafruit_esp32spi, adafruit_esp32spi_wifimanager
from adafruit_io.adafruit_io import RESTClient, AdafruitIO_RequestError

# sensor libs
import adafruit_veml6075
import adafruit_sgp30
import adafruit_bme280

# weathermeter graphics helper
import weathermeter_helper

# rate at which to refresh the pyportal and sensors, in seconds
PYPORTAL_REFRESH = 30

# anemometer defaults
anemometer_min_volts = 0.4
anemometer_max_volts = 2.0
min_wind_speed = 0.0
max_wind_speed = 32.4

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

# Set your Adafruit IO Username and Key in secrets.py
# (visit io.adafruit.com if you need to create an account,
# or if you need your Adafruit IO key.)
ADAFRUIT_IO_USER = secrets['adafruit_io_user']
ADAFRUIT_IO_KEY = secrets['adafruit_io_key']

# Create an instance of the Adafruit IO REST client
io = RESTClient(ADAFRUIT_IO_USER, ADAFRUIT_IO_KEY, wifi)

# Set up Adafruit IO Feeds
print('Grabbing Group from IO')
station_group = io.get_group('weatherstation')
print(station_group)
feed_list = station_group['feeds']
humidity_feed = feed_list[0]
temperature_feed = feed_list[1]
uv_index_feed = feed_list[2]
wind_speed_feed = feed_list[3]
"""
temperature_feed = io.get_feed('temperature')
humidity_feed = io.get_feed('humidity')
pressure_feed = io.get_feed('pressure')
altitude_feed = io.get_feed('altitude')
tvoc_feed = io.get_feed('tvoc')
eco2_feed = io.get_feed('eco2')
"""
print('Group found!')

# create an i2c object
i2c = busio.I2C(board.SCL, board.SDA)

# instantiate the sensor objects
veml = adafruit_veml6075.VEML6075(i2c, integration_time=100)
sgp30 = adafruit_sgp30.Adafruit_SGP30(i2c)
bme280 = adafruit_bme280.Adafruit_BME280_I2C(i2c)
# change this to match the location's pressure (hPa) at sea level
bme280.sea_level_pressure = 1013.25

# init. the graphics helper
gfx = weathermeter_helper.WeatherMeter_GFX()

# init. the ADC
adc = analogio.AnalogIn(board.D4)

def adc_to_wind_speed(val):
    # converts adc value, returns anemometer wind speed, in m/s
    voltage_val = val / 65535 * 3.3
    return map_range(voltage_val, 0.4, 2, 0, 32.4)

def send_to_io():
    # handle sending sensor data to Adafruit IO
    io.send_data(uv_index_feed['key'], uv_index, precision = 2)
    io.send_data(wind_speed_feed['key'], wind_speed, precision = 2)
    io.send_data(temperature_feed['key'], bme280_data[0], precision = 2)
    io.send_data(humidity_feed['key'], bme280_data[1], precision = 2)

while True:
    print('obtaining sensor data...')
    # Get uv index from veml6075
    uv_index = veml.uv_index
    # Get eco2, tvoc from sgp30
    eCO2, TVOC = sgp30.iaq_measure()
    sgp_data = [eCO2, TVOC]
    # Store bme280 data as a list
    bme280_data = [bme280.temperature, bme280.humidity,
                    bme280.pressure, bme280.altitude]
    # Get wind speed
    wind_speed = adc_to_wind_speed(adc.value)
    print(wind_speed)
    # Display sensor data on PyPortal using the gfx helper
    print('displaying sensor data...')
    gfx.display_data(uv_index, bme280_data, 
                        sgp_data, wind_speed)
    print('sensor data displayed!')

    # send sensor data to IO
    try:
        print('Sending data to Adafruit IO...')
        # TODO: Update the display with some text
        send_to_io()
        print('Data sent!')
    except AdafruitIO_RequestError as e:
        raise AdafruitIO_RequestError('ERROR: ', e)
    time.sleep(PYPORTAL_REFRESH)