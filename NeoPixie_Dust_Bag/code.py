# SPDX-FileCopyrightText: 2017 Mikey Sklar for Adafruit Industries
#
# SPDX-License-Identifier: MIT

# NeoPixie Dust Bag
# learn.adafruit.com/neopixel-pixie-dust-bag

import time

import board
import digitalio
import neopixel

try:
    import urandom as random  # for v1.0 API support
except ImportError:
    import random

neo_pin = board.D0  # DIGITAL IO pin for NeoPixel OUTPUT from GEMMA
touch_pin = board.D2  # DIGITAL IO pin for momentary touch sensor to GEMMA
pixel_count = 30  # Number of NeoPixels connected to GEMMA
delay_sec = .010  # delay between blinks, smaller numbers are faster
delay_mult = 8  # Randomization multiplier, delay speed of the effect

# initialize neopixels
pixels = neopixel.NeoPixel(
    neo_pin, pixel_count, brightness=.4, auto_write=False)

oldstate = False  # counting touch sensor button pushes
showcolor = 0  # color mode for cycling

# initialize external capacitive touch pad (active high)
button = digitalio.DigitalInOut(touch_pin)
button.direction = digitalio.Direction.INPUT
button.pull = digitalio.Pull.UP

while True:

    rcolor = 100  # swtich cycles colors, initially GOLD
    gcolor = 0
    bcolor = 0

    if showcolor == 0:  # Garden PINK
        rcolor = 242
        gcolor = 90
        bcolor = 255

    elif showcolor == 1:  # Pixie GOLD
        rcolor = 255
        gcolor = 222
        bcolor = 30

    elif showcolor == 2:  # Alchemy BLUE
        rcolor = 50
        gcolor = 255
        bcolor = 255

    elif showcolor == 3:  # Animal ORANGE
        rcolor = 255
        gcolor = 100
        bcolor = 0

    elif showcolor == 4:  # Tinker GREEN
        rcolor = 0
        gcolor = 255
        bcolor = 40

    # sparkling
    # select a random pixel
    p = random.randint(0, (pixel_count - 2))
    # color value from momentary switch
    pixels[p] = (rcolor, gcolor, bcolor)
    pixels.write()

    # delay value randomized to up to delay_mult times longer
    time.sleep(delay_sec * random.randint(0, delay_mult))

    # set to a dimmed version of the state color
    pixels[p] = (int(rcolor / 10), int(gcolor / 10), int(bcolor / 10))
    pixels.write()

    # set a neighbor pixel to an even dimmer value
    pixels[p + 1] = (int(rcolor / 15), int(gcolor / 15), int(bcolor / 15))
    pixels.write()

    # button check to cycle through color value sets
    # get the current button state
    newstate = button.value

    # Check if state changed from low to high (button/touchpad press).
    if newstate and not oldstate:
        # cycle to next color
        showcolor += 1

        # limit the cycle to the 5 colors
        if showcolor > 4:
            showcolor = 0

        # give feedback to the REPL to debug the touch pad
        # print("Color:", showcolor)

    # Set the last button state to the old state.
    oldstate = newstate
