"""
'io_house_light_temp.py'
=======================================
Control lights and monitor temperature
and humidity in a model smart house.

Learning System Guide: https://learn.adafruit.com/adafruit-io-house-lights-and-temperature

Author(s): Brent Rubell for Adafruit Industries, 2018.

Dependencies:
    - Adafruit_Blinka
        (https://github.com/adafruit/Adafruit_Blinka)
    - Adafruit_CircuitPython_SI7021
        (https://github.com/adafruit/Adafruit_CircuitPython_SI7021)
    - Adafruit_CircuitPython_NeoPixel
        (https://github.com/adafruit/Adafruit_CircuitPython_NeoPixel)
"""
# Import standard python modules
import time

# import Adafruit IO REST client
from Adafruit_IO import Client

# import Adafruit Blinka
from busio import I2C
from board import SCL, SDA, D18

# import Adafruit_CircuitPython_Si7021 Library
import adafruit_si7021

# import neopixel library
import neopixel

# `while True` loop delay, in seconds
DELAY_TIME = 5

# number of LED pixels on the NeoPixel Strip
STRIP_LED_COUNT = 34
# number of LED pixels on the NeoPixel Jewel
JEWEL_PIXEL_COUNT = 7

# Set to your Adafruit IO key.
# Remember, your key is a secret,
# so make sure not to publish it when you publish this code!
ADAFRUIT_IO_KEY = 'YOUR_IO_KEY'

# Set to your Adafruit IO username.
# (go to https://accounts.adafruit.com to find your username)
ADAFRUIT_IO_USERNAME = 'YOUR_IO_USERNAME'

# Create an instance of the REST client
aio = Client(ADAFRUIT_IO_USERNAME, ADAFRUIT_IO_KEY)

# set up Adafruit IO feeds
temperature = aio.feeds('temperature')
humidity = aio.feeds('humidity')
outdoor_lights = aio.feeds('outdoor-lights')
indoor_lights = aio.feeds('indoor-lights')

# create an i2c interface object
i2c = I2C(SCL, SDA)

# instanciate the sensor object
sensor = adafruit_si7021.SI7021(i2c)

# set up the NeoPixel strip
pixels = neopixel.NeoPixel(D18, STRIP_LED_COUNT)
pixels.fill((0,0,0))
pixels.show()

print('Adafruit IO Home: Lights and Climate Control')

while True:
    # get data from the si7021 sensor
    temperature_data = sensor.temperature
    humidity_data = sensor.relative_humidity

    # send data to adafruit io
    print('> Temperature: ', int((temperature_data * 1.8)+32))
    aio.send(temperature.key, int(temperature_data * 1.8)+32)
    print('> Humidity :', int(humidity_data))
    aio.send(temperature.key, int(humidity_data))

    # get the indoor light color picker feed
    indoor_light_data = aio.receive(indoor_lights.key)
    print('< Indoor Light HEX: ', indoor_light_data.value)
    # convert the hex values to RGB values
    red = aio.toRed(indoor_light_data.value)
    green = aio.toGreen(indoor_light_data.value)
    blue = aio.toBlue(indoor_light_data.value)

    # set the jewel's color
    for i in range(JEWEL_PIXEL_COUNT):
        pixels[i] = (red, green, blue)
        pixels.show()

    # get the outdoor light color picker feed
    outdoor_light_data = aio.receive(outdoor_lights.key)
    print('< Outdoor Light HEX: ', outdoor_light_data.value)

    # convert the hex values to RGB values
    red = aio.toRed(outdoor_light_data.value)
    green = aio.toGreen(outdoor_light_data.value)
    blue = aio.toBlue(outdoor_light_data.value)

    # set the strip color
    for j in range(JEWEL_PIXEL_COUNT, STRIP_LED_COUNT + JEWEL_PIXEL_COUNT):
        pixels[j] = (red, green, blue)
        pixels.show()

    # delay the loop to avoid timeout from Adafruit IO.
    time.sleep(DELAY_TIME)
