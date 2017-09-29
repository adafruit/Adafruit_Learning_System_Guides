# Gemma M0 IO Demo - I2C demo

from digitalio import *
from board import *
import busio
import adafruit_si7021
import time

led = DigitalInOut(D13)
led.direction = Direction.OUTPUT

i2c = busio.I2C(D2, D0)
print("I2C addresses found:", [hex(i) for i in i2c.scan()])

si7021 = adafruit_si7021.SI7021(i2c)

while True:
    print("Temp: %0.2F *C   Humidity: %0.1F %%" % (si7021.temperature, si7021.relative_humidity))
    time.sleep(1)
