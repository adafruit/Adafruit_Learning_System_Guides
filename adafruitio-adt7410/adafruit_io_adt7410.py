"""
'adafruit_io_adt7410.py'
==================================
Example of sending temperature
values to an Adafruit IO feed using
an ADT7410 breakout.

Dependencies:
    - Adafruit_Blinka
        (https://github.com/adafruit/Adafruit_Blinka)
    - Adafruit_CircuitPython_SSD1306
        (https://github.com/adafruit/Adafruit_CircuitPython_SSD1306)
    - Adafruit_CircuitPython_ADT7410
        (https://github.com/adafruit/Adafruit_CircuitPython_ADT7410)
"""
# Import standard python modules
import time

# import Adafruit SSD1306 OLED
from PIL import Image, ImageDraw, ImageFont
import adafruit_ssd1306

# import Adafruit IO REST client
from Adafruit_IO import Client

# import Adafruit CircuitPython adafruit_adt7410 library
import adafruit_adt7410

# import Adafruit Blinka
import board
import busio
import digitalio

# Delay between sensor reads, in seconds
DELAY_SECONDS = 30

# Set to your Adafruit IO key.
# Remember, your key is a secret,
# so make sure not to publish it when you publish this code!
ADAFRUIT_IO_KEY = 'ADAFRUIT_IO_KEY'

# Set to your Adafruit IO username.
# (go to https://accounts.adafruit.com to find your username)
ADAFRUIT_IO_USERNAME = 'ADAFRUIT_IO_USERNAME'

# Create an instance of the REST client
aio = Client(ADAFRUIT_IO_USERNAME, ADAFRUIT_IO_KEY)

# Set up `temperature` feed
pi_temperature = aio.feeds('temperature')

# Set up OLED
i2c_bus = busio.I2C(board.SCL, board.SDA)
oled_reset = digitalio.DigitalInOut(board.D21)
disp = adafruit_ssd1306.SSD1306_I2C(128, 32, i2c_bus, reset=oled_reset)
# Clear display.
disp.fill(0)
disp.show()

# Create blank image for drawing.
# Make sure to create image with mode '1' for 1-bit color.
width = disp.width
height = disp.height
image = Image.new('1', (width, height))
# Get drawing object to draw on image.
draw = ImageDraw.Draw(image)
# `sudo apt-get install ttf-mscorefonts-installer` to get these fonts
font_big = ImageFont.truetype('/usr/share/fonts/truetype/msttcorefonts/Arial_Bold.ttf', 16)
font_small = ImageFont.truetype('/usr/share/fonts/truetype/msttcorefonts/Arial_Bold.ttf', 12)

adt = adafruit_adt7410.ADT7410(i2c_bus, address=0x48)
adt.high_resolution = True
time.sleep(0.25)  # wait for sensor to boot up and get first reading

while True:
    # clear screen
    draw.rectangle((0, 0, width, height), outline=0, fill=0)

    # Read the temperature sensor
    tempC = adt.temperature
    tempC = round(tempC, 2)

    # display the temperature on the OLED
    draw.text((0, 0), "Temp: %0.2F *C" % tempC, font=font_big, fill=255)

    # Send temperature to Adafruit IO
    print('Sending temperature {0} C to Adafruit IO'.format(tempC))
    draw.text((0, 16), "Sending...", font=font_small, fill=255)
    disp.image(image)
    disp.show()

    aio.send(pi_temperature.key, tempC)
    draw.text((0, 16), "Sending...Done!", font=font_small, fill=255)
    disp.image(image)
    disp.show()

    # Delay for DELAY_SECONDS seconds to avoid timeout from adafruit io
    time.sleep(DELAY_SECONDS)
