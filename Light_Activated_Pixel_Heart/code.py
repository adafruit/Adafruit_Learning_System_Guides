# SPDX-FileCopyrightText: 2017 Limor Fried for Adafruit Industries
#
# SPDX-License-Identifier: MIT

import time

import board
import digitalio
import neopixel

numpix = 8  # Number of NeoPixels
ledpin = board.D1  # Digital pin # where NeoPixels are connected
sensorpin = board.D2  # Digital pin # where light sensor is connected
strip = neopixel.NeoPixel(ledpin, numpix, brightness=1.0)

# Enable internal pullup resistor on sensor pin
pin = digitalio.DigitalInOut(sensorpin)
pin.direction = digitalio.Direction.INPUT
pin.pull = digitalio.Pull.UP

while True:  # Loop forever...

    # LDR is being used as a digital (binary) sensor.  It must be
    # completely dark to turn it off, a finger may not be opaque enough!
    if pin.value:
        color = (0, 0, 0)  # Off
    else:
        color = (255, 0, 255)  # Purple

    for i in range(numpix):  # For each pixel...
        strip[i] = color  # Set to 'color'
        strip.write()  # Push data to pixels
        time.sleep(0.05)  # Pause 50 ms

    time.sleep(0.002)  # Pause 2 ms
