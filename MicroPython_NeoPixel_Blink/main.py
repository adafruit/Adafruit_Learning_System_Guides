# SPDX-FileCopyrightText: 2022 Kattni Rembor for Adafruit Industries
# SPDX-License-Identifier: MIT
import time
from machine import Pin
from neopixel import NeoPixel

power_pin = Pin(8, Pin.OUT)  # NeoPixel power is on pin 8
power_pin.on()  # Enable the NeoPixel Power

pin = Pin(5, Pin.OUT)  # Onboard NeoPixel is on pin 5
np = NeoPixel(pin, 1)  # create NeoPixel driver on pin 5 for 1 pixel

while True:
    np.fill((0, 0, 150))  # Set the NeoPixel blue
    np.write()  # Write data to the NeoPixel
    time.sleep(0.5)  # Pause for 0.5 seconds
    np.fill((0, 0, 0))  # Turn the NeoPixel off
    np.write()  # Write data to the NeoPixel
    time.sleep(0.5)  # Pause for 0.5 seconds
