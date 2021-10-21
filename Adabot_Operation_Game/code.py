# SPDX-FileCopyrightText: 2018 John Park for Adafruit Industries
#
# SPDX-License-Identifier: MIT
#
# Adabot Operation Game
#  CPX, alligator clips, copper tape, tweezers, surgery, and fun!

import board
import touchio
from adafruit_circuitplayground.express import cpx
# import time  # uncomment if testing raw read values

cap_pins = (board.A1, board.A2, board.A3, board.A4, board.A5,
            board.A6, board.A7)
touch_pads = []
for i in range(7):
    touch_pads.append(touchio.TouchIn(cap_pins[i]))
for touch_pad in touch_pads:
    touch_pad.threshold = 3500  # adjust value to fine-tune touch threshold

MAGENTA = (10, 0, 10)
VIOLET = (5, 0, 15)
BLUE = (0, 0, 20)
CYAN = (0, 10, 10)
GREEN = (0, 20, 0)
YELLOW = (10, 10, 0)
ORANGE = (15, 5, 0)
RED = (20, 0, 0)
WHITE = (3, 3, 3)

COLORS = [MAGENTA, VIOLET, BLUE, CYAN, GREEN, YELLOW, ORANGE, RED, WHITE]

cpx.pixels.fill(WHITE)

while True:
    for i in range(7):
        # uncomment block to check the raw touch pad values
        # print("raw %s value for pad " % i)
        # print(touch_pads[i].raw_value)
        # time.sleep(.5)

        if touch_pads[i].value:
            # print("Touched %s" % i)  # uncomment for debugging
            cpx.pixels.fill(RED)
            cpx.play_tone(660, 0.7)
            cpx.pixels.fill(COLORS[i])
