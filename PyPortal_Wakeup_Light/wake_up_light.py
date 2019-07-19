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
import displayio
from adafruit_display_text.label import Label
from adafruit_bitmap_font import bitmap_font
from adafruit_esp32spi import adafruit_esp32spi, adafruit_esp32spi_wifimanager
from adafruit_io.adafruit_io import RESTClient, AdafruitIO_RequestError

cwd = ("/"+__file__).rsplit('/', 1)[0] # the current working directory (where this file is)

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

# Fonts within /fonts folder
info_font = cwd+"/fonts/Nunito-Black-17.bdf"
time_font = cwd+"/fonts/Nunito-Light-75.bdf"

# create text object group
text_group = displayio.Group(max_size=6)
text_group.append(text_group)

print('loading fonts...')
glyphs = b'0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ-,.:/ '

time_font = bitmap_font.load_font(time_font)
time_font.load_glyphs(glyphs)

# Time
time_text = Label( time_font, max_glyphs=40)
time_text.x = 65
time_text.y = 120
text_group.append(time_text)
board.DISPLAY.show(time_text)

# Create an instance of the Adafruit IO REST client
io = RESTClient(ADAFRUIT_IO_USER, ADAFRUIT_IO_KEY, wifi)

while True:
    try: # WiFi Connection
        # Get and display date and time from Adafruit IO
        print('Getting time from Adafruit IO...')
        datetime = io.receive_time()
        print('displaying time...')
        time_text.text = '%02d:%02d'%(datetime[3],datetime[4])
    except (ValueError, RuntimeError) as e: # WiFi Connection Failure
        print("Failed to get data, retrying\n", e)
        wifi.reset()
        continue
    time.sleep(PYPORTAL_REFRESH)