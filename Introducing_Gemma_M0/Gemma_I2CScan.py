# Gemma IO demo - I2C scan

from digitalio import *
from board import *
import busio
import time

led = DigitalInOut(D13)
led.direction = Direction.OUTPUT

i2c = busio.I2C(D2, D0)

while True:
    print("I2C addresses found:", [hex(i) for i in i2c.scan()])
    time.sleep(2)
