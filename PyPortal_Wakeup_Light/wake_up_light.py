"""
This example uses a PyPortal and rgbw leds for a simple "wake up" light.
The strip starts to brighten 30 minutes before set wake up time.
This program assumes a neopixel strip is attached to D4 on the Adafruit PyPortal.
"""

import time
import board
import neopixel
import busio
from digitalio import DigitalInOut
from analogio import AnalogIn
import adafruit_adt7410

from adafruit_esp32spi import adafruit_esp32spi, adafruit_esp32spi_wifimanager
from adafruit_io.adafruit_io import RESTClient, AdafruitIO_RequestError

# thermometer graphics helper
import wakeup_helper

# rate at which to refresh the pyportal screen, in seconds
PYPORTAL_REFRESH = 15

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
try:
    ADAFRUIT_IO_USER = secrets['aio_username']
    ADAFRUIT_IO_KEY = secrets['aio_key']
except KeyError:
    raise KeyError('To use this code, you need to include your Adafruit IO username \
and password in a secrets.py file on the CIRCUITPY drive.')

# Create an instance of the Adafruit IO REST client
io = RESTClient(ADAFRUIT_IO_USER, ADAFRUIT_IO_KEY, wifi)

# Get the temperature feed from Adafruit IO
temperature_feed = io.get_feed('temperature')

# init. graphics helper
gfx = wakeup_helper.Thermometer_GFX(celsius=False)

# init. adt7410
i2c_bus = busio.I2C(board.SCL, board.SDA)

while True:
    try: # WiFi Connection
        # Get and display date and time form Adafruit IO
        print('Getting time from Adafruit IO...')
        datetime = io.receive_time()
        print('displaying time...')
        gfx.display_date_time(datetime)
    except (ValueError, RuntimeError) as e: # WiFi Connection Failure
        print("Failed to get data, retrying\n", e)
        wifi.reset()
        continue
    time.sleep(PYPORTAL_REFRESH)