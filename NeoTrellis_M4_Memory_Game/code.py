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

# pylint: disable=stop-iteration-return

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

key_pressed = None

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
    unassigned = [(x, y) for x in range(8) for y in range(4)]
    while unassigned:
        first_of_pair = random.choice(unassigned)
        unassigned.remove(first_of_pair)
        second_of_pair = random.choice(unassigned)
        unassigned.remove(second_of_pair)
        random_color = random.choice(COLORS)
        pixel_colors[index_of(first_of_pair)] = random_color
        pixel_colors[index_of(second_of_pair)] = random_color

def handle_key(key, _found_pairs, _first_pixel):
    if key is None:
        return _found_pairs, _first_pixel
    key_color = pixel_colors[index_of(key)]
    if key_color is not None:
        trellis.pixels[key] = pixel_colors[index_of(key)]
        time.sleep(0.5)
        if _first_pixel and _first_pixel != key:
            if key_color == pixel_colors[index_of(_first_pixel)]:
                pixel_colors[index_of(_first_pixel)] = None
                pixel_colors[index_of(key)] = None
                for _ in range(5):
                    trellis.pixels[_first_pixel] = 0xFFFFFF
                    trellis.pixels[key] = 0xFFFFFF
                    time.sleep(0.1)
                    trellis.pixels[_first_pixel] = 0x000000
                    trellis.pixels[key] = 0x000000
                    time.sleep(0.1)
                trellis.pixels[_first_pixel] = 0x444444
                trellis.pixels[key] = 0x444444
                return _found_pairs + 1, None
            else:
                trellis.pixels[_first_pixel] = 0x000000
                trellis.pixels[key] = 0x000000
                return _found_pairs, None
        else:
            return _found_pairs, key
    return _found_pairs, None

def check_for_key(last_pressed):
    now_pressed = set(trellis.pressed_keys)
    new_presses = now_pressed - last_pressed
    if new_presses:
        return now_pressed, list(new_presses)[0]
    return now_pressed, None

demo_mode_enabled = True
while True:
    trellis.pixels.fill(0x000000)
    assign_colors()
    found_pairs = 0
    first_pixel = None
    remaining = [(x, y) for x in range(8) for y in range(4)]
    while found_pairs < 16:
        if demo_mode_enabled:
            previously_pressed, key_pressed = check_for_key(previously_pressed)
            if key_pressed:
                demo_mode_enabled = False
                break
            first = random.choice(remaining)
            remaining.remove(first)
            found_pairs, first_pixel = handle_key(first, found_pairs, first_pixel)
            previously_pressed, key_pressed = check_for_key(previously_pressed)
            if key_pressed:
                demo_mode_enabled = False
                break
            c = pixel_colors[index_of(first)]
            match = random.choice([x for x in remaining if pixel_colors[index_of(x)] == c])
            found_pairs, first_pixel = handle_key(match, found_pairs, first_pixel)
            remaining.remove(match)
        else:
            previously_pressed, key_pressed = check_for_key(previously_pressed)
            found_pairs, first_pixel = handle_key(key_pressed, found_pairs, first_pixel)
    if found_pairs == 16:
        splash()
