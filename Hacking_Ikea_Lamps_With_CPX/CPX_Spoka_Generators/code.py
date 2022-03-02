# SPDX-FileCopyrightText: 2018 Kattni Rembor for Adafruit Industries
#
# SPDX-License-Identifier: MIT

import time
from rainbowio import colorwheel
from adafruit_circuitplayground.express import cpx


# pylint: disable=stop-iteration-return
def cycle_sequence(seq):
    while True:
        for elem in seq:
            yield elem


def rainbow_lamp(seq):
    g = cycle_sequence(seq)
    while True:
        cpx.pixels.fill(colorwheel(next(g)))
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

heart_rate = 0
last_heart_beat = time.monotonic()
next_heart_beat = last_heart_beat + heart_rate

rainbow = None

cpx.detect_taps = 2
cpx.pixels.brightness = 0.2

while True:
    now = time.monotonic()

    if cpx.tapped or rainbow is None:
        rainbow = rainbow_lamp(next(color_sequences))

    if cpx.shake(shake_threshold=20):
        heart_rate = next(heart_rates)
        last_heart_beat = now
        next_heart_beat = last_heart_beat + heart_rate

    if now >= next_heart_beat:
        next(rainbow)
        last_heart_beat = now
        next_heart_beat = last_heart_beat + heart_rate
