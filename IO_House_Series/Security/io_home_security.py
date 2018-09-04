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
    - picamera
"""
# Import standard python modules
import time
import base64
import os
# import Adafruit IO REST client
from Adafruit_IO import Client, Feed, RequestError

# import Adafruit Blinka
from board import SCL, SDA, D18, D22, D24
from busio import I2C
import digitalio
import neopixel_write

# import Adafruit_CircuitPython_SGP30 and picam
import adafruit_sgp30
import picamera

# NeoPixels Commands
PIXELS_OFF = bytearray([0, 0, 0])
PIXELS_ON = bytearray([0, 255, 0])

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
pixel_strip = digitalio.DigitalInOut(D18)
pixel_strip.direction = digitalio.Direction.OUTPUT
neopixel_write.neopixel_write(pixel_strip, PIXELS_OFF)

print('Adafruit IO Home: Security')

def alarm_trigger():
  """Alarm is triggered by the dashboard toggle
  and a sensor detecting movement.
  """
  print('* SYSTEM ALARM!')
  for j in range(0, 5):
    neopixel_write.neopixel_write(pixel_strip, PIXELS_ON)
    time.sleep(0.5)
    neopixel_write.neopixel_write(pixel_strip, PIXELS_OFF)
  # turn pixels off after alarm animation
  neopixel_write.neopixel_write(pixel_strip, PIXELS_OFF)

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
    except:
      print('Sending camera image failed...')

  # Alarm System 
  is_alarm = aio.receive(alarm_feed.key)

  if (is_alarm.value == "ON"):
    # sample the current hour
    cur_time = time.localtime()
    cur_hour = time.tm_hour
    if (cur_hour > ALARM_HOUR and is_pir_activated == True):
      alarm_trigger()

  prev_pir_value = door_sensor.value
  time.sleep(LOOP_INTERVAL)


