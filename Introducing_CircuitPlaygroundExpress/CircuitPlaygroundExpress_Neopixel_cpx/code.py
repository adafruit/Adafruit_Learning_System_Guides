# SPDX-FileCopyrightText: 2017 Kattni Rembor for Adafruit Industries
#
# SPDX-License-Identifier: MIT

import time
from rainbowio import colorwheel
from adafruit_circuitplayground.express import cpx

# choose which demos to play
# 1 means play, 0 means don't!
simpleCircleDemo = 1
flashDemo = 1
rainbowDemo = 1
rainbowCycleDemo = 1

RED = (10, 0, 0)
YELLOW = (10, 10, 0)
GREEN = (0, 10, 0)
AQUA = (0, 10, 10)
BLUE = (0, 0, 10)
PURPLE = (10, 0, 10)
BLACK = (0, 0, 0)

while True:
    cpx.pixels.brightness = 0.2
    if simpleCircleDemo:
        print('Simple Circle Demo')
        for i in range(len(cpx.pixels)):
            cpx.pixels[i] = RED
            time.sleep(.05)
        time.sleep(1)

        for i in range(len(cpx.pixels)):
            cpx.pixels[i] = YELLOW
            time.sleep(.05)
        time.sleep(1)

        for i in range(len(cpx.pixels)):
            cpx.pixels[i] = GREEN
            time.sleep(.05)
        time.sleep(1)

        for i in range(len(cpx.pixels)):
            cpx.pixels[i] = AQUA
            time.sleep(.05)
        time.sleep(1)

        for i in range(len(cpx.pixels)):
            cpx.pixels[i] = BLUE
            time.sleep(.05)
        time.sleep(1)

        for i in range(len(cpx.pixels)):
            cpx.pixels[i] = PURPLE
            time.sleep(.05)
        time.sleep(1)

        for i in range(len(cpx.pixels)):
            cpx.pixels[i] = BLACK
            time.sleep(.05)
        time.sleep(1)

    if flashDemo:
        print('Flash Demo')
        cpx.pixels.fill((255, 0, 0))
        time.sleep(0.25)
        cpx.pixels.fill((0, 255, 0))
        time.sleep(0.25)
        cpx.pixels.fill((0, 0, 255))
        time.sleep(0.25)
        cpx.pixels.fill((255, 255, 255))
        time.sleep(0.25)

    if rainbowDemo:
        print('Rainbow Demo')
        for j in range(255):
            for i in range(len(cpx.pixels)):
                idx = int(i + j)
                cpx.pixels[i] = colorwheel(idx & 255)
            time.sleep(.001)

    if rainbowCycleDemo:
        print('Rainbow Cycle Demo')
        for j in range(255):
            for i in range(len(cpx.pixels)):
                idx = int((i * 256 / len(cpx.pixels)) + j * 10)
                cpx.pixels[i] = colorwheel(idx & 255)
            time.sleep(.001)
