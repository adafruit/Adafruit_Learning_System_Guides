# SPDX-FileCopyrightText: 2019 Kattni Rembor for Adafruit Industries
#
# SPDX-License-Identifier: MIT

import board
import digitalio
import adafruit_lis3dh
import touchio
import time
import neopixel
import adafruit_thermistor

pixels = neopixel.NeoPixel(board.NEOPIXEL, 10, brightness=0.2)

i2c = board.I2C()  # uses board.SCL and board.SDA
# i2c = board.STEMMA_I2C()  # For using the built-in STEMMA QT connector on a microcontroller
int1 = digitalio.DigitalInOut(board.ACCELEROMETER_UNTERRUPT)
lis3dh = adafruit_lis3dh.LIS3DH_I2C(i2c, int1=int1)

circuit_playground_temperature = adafruit_thermistor.Thermistor(board.TEMPERATURE, 10000, 10000, 25, 3950)

touch_A1 = touchio.TouchIn(board.A1)
touch_A2 = touchio.TouchIn(board.A2)

led = digitalio.DigitalInOut(board.D13)
led.direction = digitalio.Direction.OUTPUT

button_A = digitalio.DigitalInOut(board.BUTTON_A)
button_A.direction = digitalio.Direction.INPUT
button_A.pull = digitalio.Pull.DOWN

while True:
    x, y, z = lis3dh.acceleration

    if button_A.value:
        led.value = True
	else:
        led.value = False

    print("Temperature:", circuit_playground_temperature.temperature)
    print("Acceleration:", x, y, z)

    if touch_A1.value:
        pixels.fill((255, 0, 0))
    if touch_A2.value:
        pixels.fill((0, 0, 255))
    else:
        pixels.fill((0, 0, 0))
    
    time.sleep(0.01)
