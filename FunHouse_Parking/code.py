# SPDX-FileCopyrightText: Copyright (c) 2021 John Park for Adafruit
#
# SPDX-License-Identifier: MIT
# FunHouse Parking Assistant

import time
import board
import adafruit_hcsr04
import neopixel
from adafruit_funhouse import FunHouse

SLOW_DISTANCE = 30  # distance (in centimeters) when you should slow
STOP_DISTANCE = 8  # distance when you should hit those brakes

GREEN = 0x00FF00
AMBER = 0xF0D000
RED = 0xFF0000


funhouse = FunHouse(default_bg=None, scale=3)
funhouse.peripherals.dotstars.brightness = 0.05
funhouse.peripherals.dotstars.fill(GREEN)

pixel_pin = board.A2
num_pixels = 30
pixels = neopixel.NeoPixel(pixel_pin, num_pixels, brightness=0.3, auto_write=False)

sonar = adafruit_hcsr04.HCSR04(trigger_pin=board.A0, echo_pin=board.A1)

while True:
    try:
        print((sonar.distance,))

        if sonar.distance > SLOW_DISTANCE:
            funhouse.peripherals.dotstars.fill(GREEN)
            pixels.fill(GREEN)
            pixels.show()
        elif sonar.distance < SLOW_DISTANCE and sonar.distance > STOP_DISTANCE:
            funhouse.peripherals.dotstars.fill(AMBER)
            pixels.fill(AMBER)
            pixels.show()
            funhouse.peripherals.play_tone(1000, 0.3)
        elif sonar.distance < STOP_DISTANCE:
            funhouse.peripherals.dotstars.fill(RED)
            pixels.fill(RED)
            pixels.show()
            funhouse.peripherals.play_tone(2600, 0.3)

    except RuntimeError:
        print("Retrying!")
    time.sleep(0.01)
