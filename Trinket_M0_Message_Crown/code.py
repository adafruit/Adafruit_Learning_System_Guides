# SPDX-FileCopyrightText: 2021 Charlyn Gonda for Adafruit Industries
#
# SPDX-License-Identifier: MIT
#
import time
import board
from rainbowio import colorwheel
import neopixel

pixel_pin = board.D4
num_pixels = 13

pixels = neopixel.NeoPixel(pixel_pin, num_pixels, brightness=0.3, auto_write=False)

# Lights up the message letter by letter
def spell(color, wait):
    for i in range(num_pixels-1, -1, -1):
        pixels[i] = color
        time.sleep(wait)
        pixels.show()
    time.sleep(0.5)

# Lights up a word, given a startIndex and stopIndex
def show_word(startIndex, endIndex, color, wait):
    pixels.fill(OFF)
    pixels.show()
    time.sleep(0.1)

    for i in range(startIndex, endIndex-1, -1):
        pixels[i] = color

    pixels.show()
    time.sleep(wait)

# Lights up every even-numbered index of neopixel
def alternate(p1, color, wait):
    for i in range(num_pixels):
        if i % 2 == 0:
            pixels[i] = color
        else:
            pixels[i] = OFF
    pixels.show()
    time.sleep(wait)

# Lights up every odd-numbered index of neopixel
def alternate_reverse(p1, color, wait):
    for i in range(num_pixels):
        if i % 2 == 1:
            pixels[i] = color
        else:
            pixels[i] = OFF
    pixels.show()
    time.sleep(wait)

# Full rainbow!
def rainbow_cycle(wait):
    for j in range(255):
        for i in range(num_pixels):
            rc_index = (i * 256 // num_pixels) + j
            pixels[i] = colorwheel(rc_index & 255)
        pixels.show()
        time.sleep(wait)

RED = (255, 0, 0)
YELLOW = (255, 150, 0)
ORANGE = (255, 40, 0)
GREEN = (0, 255, 0)
CYAN = (0, 255, 255)
BLUE = (0, 0, 255)
PURPLE = (180, 0, 255)
MAGENTA = (255, 0, 20)
JADE = (0, 255, 40)
OFF = (0,0,0)

ALT_WAIT = 0.5
CHASE_WAIT = 0.1
WORD_WAIT = 1

while True:
    # indices for "birthday" is from 12 - 5
    show_word(12, 5, MAGENTA, WORD_WAIT)

    # indices for "boss" is from 4 - 0
    show_word(4, 0, JADE, WORD_WAIT)

    # again!
    show_word(12, 5, ORANGE, WORD_WAIT)
    show_word(4, 0, YELLOW, WORD_WAIT)

    spell(GREEN, CHASE_WAIT)
    spell(CYAN, CHASE_WAIT)
    spell(PURPLE, CHASE_WAIT)

    alternate(pixels, JADE, ALT_WAIT)
    alternate_reverse(pixels, ORANGE, ALT_WAIT)

    alternate(pixels, MAGENTA, ALT_WAIT)
    alternate_reverse(pixels, BLUE, ALT_WAIT)

    alternate(pixels, PURPLE, ALT_WAIT)
    alternate_reverse(pixels, GREEN, ALT_WAIT)

    alternate(pixels, CYAN, ALT_WAIT)
    alternate_reverse(pixels, MAGENTA, ALT_WAIT)

    rainbow_cycle(0)
    rainbow_cycle(0) # higher number, slower rainbow
