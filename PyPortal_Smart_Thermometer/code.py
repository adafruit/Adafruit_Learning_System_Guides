"""
PyPortal Smart Thermometer
==============================================
Turn your PyPortal into an internet-connected
thermometer with Adafruit IO

Author: Brent Rubell for Adafruit Industries, 2019
"""
import time
import board
import neopixel
import busio
from digitalio import DigitalInOut
from analogio import AnalogIn
import adafruit_adt7410

from adafruit_esp32spi import adafruit_esp32spi, adafruit_esp32spi_wifimanager
from adafruit_io.adafruit_io import IO_HTTP, AdafruitIO_RequestError

# thermometer graphics helper
import thermometer_helper

# rate at which to refresh the pyportal screen, in seconds
PYPORTAL_REFRESH = 2

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

# Create an instance of the IO_HTTP client
io = IO_HTTP(ADAFRUIT_IO_USER, ADAFRUIT_IO_KEY, wifi)

# Get the temperature feed from Adafruit IO
temperature_feed = io.get_feed('temperature')

# init. graphics helper
gfx = thermometer_helper.Thermometer_GFX(celsius=False)

# init. adt7410
i2c_bus = busio.I2C(board.SCL, board.SDA)
adt = adafruit_adt7410.ADT7410(i2c_bus, address=0x48)
adt.high_resolution = True

# init. the light sensor
light_sensor = AnalogIn(board.LIGHT)

def set_backlight(val):
    """Adjust the TFT backlight.
    :param val: The backlight brightness. Use a value between ``0`` and ``1``, where ``0`` is
                off, and ``1`` is 100% brightness.
    """
    val = max(0, min(1.0, val))
    board.DISPLAY.auto_brightness = False
    board.DISPLAY.brightness = val

while True:
    # read the light sensor
    light_value = light_sensor.value
    print('Light Value: ', light_value)
    # read the temperature sensor
    temperature = adt.temperature
    try: # WiFi Connection
        if light_value < 1000: # turn on the backlight
            set_backlight(1)
            print('displaying temperature...')
            gfx.display_temp(temperature)
            # Get and display date and time form Adafruit IO
            print('Getting time from Adafruit IO...')
            datetime = io.receive_time()
            print('displaying time...')
            gfx.display_date_time(datetime)
        else: # turn off the backlight
            set_backlight(0)
        try: # send temperature data to IO
            gfx.display_io_status('Sending data...')
            print('Sending data to Adafruit IO...')
            io.send_data(temperature_feed['key'], temperature)
            print('Data sent!')
            gfx.display_io_status('Data sent!')
        except AdafruitIO_RequestError as e:
            raise AdafruitIO_RequestError('IO Error: ', e)
    except (ValueError, RuntimeError) as e: # WiFi Connection Failure
        print("Failed to get data, retrying\n", e)
        wifi.reset()
        continue
    time.sleep(PYPORTAL_REFRESH)
