# SPDX-FileCopyrightText: 2024 Liz Clark for Adafruit Industries
# SPDX-License-Identifier: MIT

import time
import board
from rainbowio import colorwheel
import adafruit_dotstar as dotstar

clock_pin = board.CLOCK
data_pin = board.DATA
num_dots = 30
speed = 0.01
brightness = 0.2
order = "PGBR" # PGBR, PGRB, PRBG or PRGB
dots = dotstar.DotStar(clock_pin, data_pin, num_dots,
					   brightness=brightness, auto_write=True,
					   pixel_order=order)

hue = 0
dots.fill(colorwheel(hue))

while True:
    hue = (hue + 1) % 256
    dots.fill(colorwheel(hue))
    time.sleep(speed)
