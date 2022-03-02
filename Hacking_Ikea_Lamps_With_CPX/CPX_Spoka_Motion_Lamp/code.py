# SPDX-FileCopyrightText: 2018 Kattni Rembor for Adafruit Industries
#
# SPDX-License-Identifier: MIT

import time
from rainbowio import colorwheel
from adafruit_circuitplayground.express import cpx


# pylint: disable=redefined-outer-name
def upright(x, y, z):
    return abs(x) < accel_threshold \
           and abs(y) < accel_threshold \
           and abs(9.8 - z) < accel_threshold


def right_side(x, y, z):
    return abs(-9.8 - x) < accel_threshold \
           and abs(y) < accel_threshold \
           and abs(z) < accel_threshold


def left_side(x, y, z):
    return abs(9.8 - x) < accel_threshold \
           and abs(y) < accel_threshold \
           and abs(z) < accel_threshold


# pylint: enable=redefined-outer-name


def cycle_sequence(seq):
    while True:
        for elem in seq:
            yield elem


def rainbow_lamp(seq):
    g = cycle_sequence(seq)
    while True:
        # pylint: disable=stop-iteration-return
        cpx.pixels.fill(colorwheel(next(g)))
        yield


def brightness_lamp():
    brightness_value = cycle_sequence([0.4, 0.6, 0.8, 1, 0.2])
    while True:
        # pylint: disable=stop-iteration-return
        cpx.pixels.brightness = next(brightness_value)
        yield


color_sequences = cycle_sequence([
    range(256),  # rainbow_cycle
    [0],  # red
    [10],  # orange
    [30],  # yellow
    [85],  # green
    [137],  # cyan
    [170],  # blue
    [213],  # purple
    [0, 10, 30, 85, 137, 170, 213],  # party mode
])

heart_rates = cycle_sequence([0, 0.5, 1.0])

brightness = brightness_lamp()

heart_rate = 0
last_heart_beat = time.monotonic()
next_heart_beat = last_heart_beat + heart_rate

rainbow = None
state = None
hold_end = None

cpx.detect_taps = 2
accel_threshold = 2
cpx.pixels.brightness = 0.2
hold_time = 1

while True:
    now = time.monotonic()
    x, y, z = cpx.acceleration

    if left_side(x, y, z):
        if state is None or not state.startswith("left"):
            hold_end = now + hold_time
            state = "left"
        elif (state == "left"
              and hold_end is not None
              and now >= hold_end):
            state = "left-done"
            next(brightness)
    elif right_side(x, y, z):
        if state is None or not state.startswith("right"):
            hold_end = now + hold_time
            state = "right"
        elif (state == "right"
              and hold_end is not None
              and now >= hold_end):
            state = "right-done"
            heart_rate = next(heart_rates)
            last_heart_beat = now
            next_heart_beat = last_heart_beat + heart_rate
    elif upright(x, y, z):
        if state != "upright":
            hold_end = None
            state = "upright"

    if cpx.tapped or rainbow is None:
        rainbow = rainbow_lamp(next(color_sequences))

    if now >= next_heart_beat:
        next(rainbow)
        last_heart_beat = now
        next_heart_beat = last_heart_beat + heart_rate

    if cpx.shake(shake_threshold=20):
        cpx.pixels.brightness = 0
