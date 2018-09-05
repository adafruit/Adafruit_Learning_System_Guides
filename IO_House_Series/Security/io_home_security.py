"""
'io_home_security.py'
=======================================
Secure and monitor your home with
Adafruit IO.

Learning System Guide: https://learn.adafruit.com/adafruit-io-home-security

Author(s): Brent Rubell for Adafruit Industries, 2018.

Dependencies:
    - Adafruit_Blinka
        (https://github.com/adafruit/Adafruit_Blinka)
    - Adafruit_CircuitPython_SGP30
        (https://github.com/adafruit/Adafruit_CircuitPython_SGP30)
    - Adafruit_CircuitPython_NeoPixel
        (https://github.com/adafruit/Adafruit_CircuitPython_NeoPixel)
    - picamera
        (https://github.com/waveform80/picamera)
"""
# Import standard python modules
import time
import base64
# import Adafruit IO REST client
from Adafruit_IO import Client, RequestError

# import SGP30, NeoPixel and picam libraries
import neopixel
import adafruit_sgp30
import picamera

# import Adafruit Blinka
from board import SCL, SDA, D18, D22, D24
from busio import I2C
import digitalio

# Number of NeoPixels connected to the strip
NUM_PIXELS_STRIP = 60
# Number of NeoPixels connected to the NeoPixel Jewel
NUM_PIXELS_JEWEL = 6
RED = (255, 0, 0)

# Set to the hour at which to arm the alarm system, 24hr time
ALARM_HOUR = 16

# Set to the interval between loop execution, in seconds
LOOP_INTERVAL = 2

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
tvoc_feed = aio.feeds('tvoc')
eco2_feed = aio.feeds('eco2')
door_feed = aio.feeds('front-door')
motion_feed = aio.feeds('motion-detector')
alarm_feed = aio.feeds('home-alarm')
outdoor_lights_feed = aio.feeds('outdoor-lights')
indoor_lights_Feed = aio.feeds('indoor-lights')
picam_feed = aio.feeds('picam')

# set up picamera
camera = picamera.PiCamera()
# set the resolution of the pi camera
# note: you can only send images <100kb to feeds
camera.resolution = (200, 200)

# set up door sensor
door_sensor = digitalio.DigitalInOut(D24)
door_sensor.direction = digitalio.Direction.INPUT

# set up motion sensor
pir_sensor = digitalio.DigitalInOut(D22)
pir_sensor.direction = digitalio.Direction.INPUT
prev_pir_value = pir_sensor.value
is_pir_activated = False

# set up sgp30
i2c_bus = I2C(SCL, SDA, frequency=100000)
sgp30 = adafruit_sgp30.Adafruit_SGP30(i2c_bus)

# set up the neopixel strip
pixels = neopixel.NeoPixel(D18, NUM_PIXELS_STRIP)
pixels.fill((0, 0, 0))
pixels.show()

def alarm_trigger():
    """Alarm is triggered by the dashboard toggle
    and a sensor detecting movement.
    """
    print('* SYSTEM ALARM!')
    for j in range(NUM_PIXELS_JEWEL):
        pixels[j] = RED
        pixels.show()
    time.sleep(0.5)
    # turn pixels off after alarm
    pixels.fill((0, 0, 0))
    pixels.show()

print('Adafruit IO Home: Security')

while True:
    # read SGP30
    co2eq, tvoc = sgp30.iaq_measure()
    print("CO2eq = %d ppm \t TVOC = %d ppb" % (co2eq, tvoc))
    # send SGP30 values to Adafruit IO
    aio.send(eco2_feed.key, co2eq)
    aio.send(tvoc_feed.key, tvoc)
    time.sleep(0.5)

    # read/send door sensor
    if door_sensor.value:
        print('Door Open!')
        # change indicator block to red
        aio.send(door_feed.key, 3)
    else:
        print('Door Closed.')
        # reset indicator block to green
        aio.send(door_feed.key, 0)

    # read/send motion sensor
    if door_sensor.value:
        if not prev_pir_value:
            print('Motion detected!')
            is_pir_activated = True
            # change indicator block to red
            aio.send(motion_feed.key, 3)
    else:
        if prev_pir_value:
            print('Motion ended.')
            is_pir_activated = False
            # reset indicator block to green
            aio.send(motion_feed.key, 0)

    camera.capture('picam.jpg')
    print('snap!')
    with open("picam.jpg", "rb") as imageFile:
        image = base64.b64encode(imageFile.read())
        send_str = image.decode("utf-8")
        try:
            aio.send(picam_feed.key, send_str)
            print('sent to AIO!')
        except RequestError:
            print('Sending camera image failed...')

    # Alarm System
    is_alarm = aio.receive(alarm_feed.key)

    if is_alarm.value == "ON":
        # sample the current hour
        cur_time = time.localtime()
        cur_hour = time.tm_hour
        if (cur_hour > ALARM_HOUR and is_pir_activated is True):
            alarm_trigger()

    prev_pir_value = door_sensor.value
    time.sleep(LOOP_INTERVAL)
