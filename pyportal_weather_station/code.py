"""
PyPortal Weather Station
==============================================
Turn your PyPortal into a weaterstation with
Adafruit IO

Author: Brent Rubell for Adafruit Industries, 2019
"""
import time
import board
import neopixel
import busio
import analogio
from simpleio import map_range
from digitalio import DigitalInOut

from adafruit_esp32spi import adafruit_esp32spi, adafruit_esp32spi_wifimanager
from adafruit_io.adafruit_io import IO_HTTP, AdafruitIO_RequestError

# sensor libs
import adafruit_veml6075
import adafruit_sgp30
import adafruit_bme280

# weatherstation graphics helper
import weatherstation_helper

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
ADAFRUIT_IO_USER = secrets['aio_username']
ADAFRUIT_IO_KEY = secrets['aio_key']

# Create an instance of the Adafruit IO HTTP client
io = IO_HTTP(ADAFRUIT_IO_USER, ADAFRUIT_IO_KEY, wifi)

# create an i2c object
i2c = busio.I2C(board.SCL, board.SDA)

# instantiate the sensor objects
veml = adafruit_veml6075.VEML6075(i2c, integration_time=100)
sgp30 = adafruit_sgp30.Adafruit_SGP30(i2c)
bme280 = adafruit_bme280.Adafruit_BME280_I2C(i2c)
# change this to match the location's pressure (hPa) at sea level
bme280.sea_level_pressure = 1013.25

# init. the graphics helper
gfx = weatherstation_helper.WeatherStation_GFX()

# init. the ADC
adc = analogio.AnalogIn(board.D4)

# Set up Adafruit IO Feeds
print('Getting Group data from Adafruit IO...')
station_group = io.get_group('weatherstation')
feed_list = station_group['feeds']
altitude_feed = feed_list[0]
eco2_feed = feed_list[1]
humidity_feed = feed_list[2]
pressure_feed = feed_list[3]
temperature_feed = feed_list[4]
tvoc_feed = feed_list[5]
uv_index_feed = feed_list[6]
wind_speed_feed = feed_list[7]

def adc_to_wind_speed(val):
    """Returns anemometer wind speed, in m/s.
    :param int val: ADC value
    """
    voltage_val = val / 65535 * 3.3
    return map_range(voltage_val, 0.4, 2, 0, 32.4)

def send_to_io():
    # handle sending sensor data to Adafruit IO
    io.send_data(uv_index_feed['key'], uv_index)
    io.send_data(wind_speed_feed['key'], wind_speed)
    io.send_data(temperature_feed['key'], bme280_data[0])
    io.send_data(humidity_feed['key'], bme280_data[1])
    io.send_data(pressure_feed['key'], bme280_data[2])
    io.send_data(altitude_feed['key'], bme280_data[3])
    io.send_data(eco2_feed['key'], sgp_data[0])
    io.send_data(tvoc_feed['key'], sgp_data[1])

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
    # Display sensor data on PyPortal using the gfx helper
    print('displaying sensor data...')
    gfx.display_data(uv_index, bme280_data,
                     sgp_data, wind_speed)
    print('sensor data displayed!')
    try:
        try:
            print('Sending data to Adafruit IO...')
            gfx.display_io_status('Sending data to IO...')
            send_to_io()
            gfx.display_io_status('Data Sent!')
            print('Data sent!')
        except AdafruitIO_RequestError as e:
            raise AdafruitIO_RequestError('IO Error: ', e)
    except (ValueError, RuntimeError) as e:
        print("Failed to get data, retrying\n", e)
        wifi.reset()
        continue
    time.sleep(PYPORTAL_REFRESH)
