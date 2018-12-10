"""
NeoTrellis M4 Express Memory Game

Adafruit invests time and resources providing this open source code.
Please support Adafruit and open source hardware by purchasing
products from Adafruit!

Written by Dave Astels for Adafruit Industries
Copyright (c) 2018 Adafruit Industries
Licensed under the MIT license.

All text above must be included in any redistribution.
"""

# pylint: disable=global-statement,stop-iteration-return

import time
import random
import adafruit_trellism4

COLORS = [0xFF0000, 0xFFFF00, 0x00FF00, 0x00FFFF, 0x0000FF, 0xFF00FF]

trellis = adafruit_trellism4.TrellisM4Express(rotation=0)
trellis.pixels.brightness = 0.1
trellis.pixels.fill(0)

pixel_colors = [None] * 32
found_pairs = 0
previously_pressed = set([])
first_pixel = None


def index_of(coord):
    x, y = coord
    return y * 8 + x

def wheel(pos):
    # Input a value 0 to 255 to get a color value.
    # The colours are a transition r - g - b - back to r.
    if pos < 0 or pos > 255:
        return 0, 0, 0
    if pos < 85:
        return int(255 - pos*3), int(pos*3), 0
    if pos < 170:
        pos -= 85
        return 0, int(255 - pos*3), int(pos*3)
    pos -= 170
    return int(pos * 3), 0, int(255 - (pos*3))

def cycle_sequence(seq):
    while True:
        for elem in seq:
            yield elem

def rainbow_lamp(seq):
    g = cycle_sequence(seq)
    while True:
        trellis.pixels.fill(wheel(next(g)))
        yield

def splash():
    rainbow = rainbow_lamp(range(0, 256, 8))
    for _ in range(64):
        next(rainbow)
        time.sleep(0.005)

def assign_colors():
    remaining = [(x, y) for x in range(8) for y in range(4)]
    while remaining:
        first = random.choice(remaining)
        remaining.remove(first)
        second = random.choice(remaining)
        remaining.remove(second)
        c = random.choice(COLORS)
        pixel_colors[index_of(first)] = c
        pixel_colors[index_of(second)] = c

def handle_key(key):
    if key is None:
        return found_pairs, first_pixel
    key_color = pixel_colors[index_of(key)]
    if key_color is not None:
        trellis.pixels[key] = pixel_colors[index_of(key)]
        time.sleep(0.5)
        if first_pixel:           # we're trying to match a second pixel
            if key_color == pixel_colors[index_of(first_pixel)]:
                pixel_colors[index_of(first_pixel)] = None
                pixel_colors[index_of(key)] = None
                for _ in range(5):
                    trellis.pixels[first_pixel] = 0xFFFFFF
                    trellis.pixels[key] = 0xFFFFFF
                    time.sleep(0.1)
                    trellis.pixels[first_pixel] = 0x000000
                    trellis.pixels[key] = 0x000000
                    time.sleep(0.1)
                trellis.pixels[first_pixel] = 0x444444
                trellis.pixels[key] = 0x444444
                return found_pairs + 1, None

            else:
                trellis.pixels[first_pixel] = 0x000000
                trellis.pixels[key] = 0x000000
                return found_pairs, None
        else:
            return found_pairs, key
    return found_pairs, None

def check_for_key():
    global previously_pressed
    now_pressed = set(trellis.pressed_keys)
    new_presses = now_pressed - previously_pressed
    if new_presses:
        return list(new_presses)[0]
    return None

def demo_mode():
    global found_pairs, first_pixel
    while True:
        trellis.pixels.fill(0x000000)
        assign_colors()
        found_pairs = 0
        remaining = [(x, y) for x in range(8) for y in range(4)]
        while found_pairs < 16:
            if check_for_key():
                return
            first = random.choice(remaining)
            remaining.remove(first)
            found_pairs, first_pixel = handle_key(first)
            if check_for_key():
                return
            c = pixel_colors[index_of(first)]
            match = random.choice([x for x in remaining if pixel_colors[index_of(x)] == c])
            found_pairs, first_pixel = handle_key(match)
            remaining.remove(match)
        splash()

while True:
    demo_mode()

    trellis.pixels.fill(0x000000)
    assign_colors()
    found_pairs = 0
    first_pixel = None
    while found_pairs < 16:
        found_pairs, first_pixel = handle_key(check_for_key())
    splash()
