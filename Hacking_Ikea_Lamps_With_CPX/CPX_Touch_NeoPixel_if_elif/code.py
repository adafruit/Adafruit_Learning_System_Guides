# SPDX-FileCopyrightText: 2018 Kattni Rembor for Adafruit Industries
#
# SPDX-License-Identifier: MIT

from adafruit_circuitplayground.express import cpx

while True:
    if cpx.touch_A1:
        cpx.pixels.fill((255, 0, 0))  # red
    elif cpx.touch_A2:
        cpx.pixels.fill((255, 40, 0))  # orange
    elif cpx.touch_A3:
        cpx.pixels.fill((255, 150, 0))  # yellow
    elif cpx.touch_A4:
        cpx.pixels.fill((0, 255, 0))  # green
    elif cpx.touch_A5:
        cpx.pixels.fill((0, 0, 255))  # blue
    elif cpx.touch_A6:
        cpx.pixels.fill((180, 0, 255))  # purple
    elif cpx.touch_A7:
        cpx.pixels.fill((0, 0, 0))  # off
