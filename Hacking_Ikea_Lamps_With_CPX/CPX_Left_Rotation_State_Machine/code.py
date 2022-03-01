# SPDX-FileCopyrightText: 2018 Kattni Rembor for Adafruit Industries
#
# SPDX-License-Identifier: MIT

import time

from adafruit_circuitplayground.express import cpx


# pylint: disable=redefined-outer-name


def upright(x, y, z):
    x_up = abs(x) < accel_threshold
    y_up = abs(y) < accel_threshold
    z_up = abs(9.8 - z) < accel_threshold
    return x_up and y_up and z_up


def left_side(x, y, z):
    x_side = abs(9.8 - x) < accel_threshold
    y_side = abs(y) < accel_threshold
    z_side = abs(z) < accel_threshold

    return x_side and y_side and z_side


state = None
hold_end = None

accel_threshold = 2
hold_time = 1

while True:
    x, y, z = cpx.acceleration
    if left_side(x, y, z):
        if state is None or not state.startswith("left"):
            hold_end = time.monotonic() + hold_time
            state = "left"
            print("Entering state 'left'")
        elif (state == "left"
              and hold_end is not None
              and time.monotonic() >= hold_end):
            state = "left-done"
            print("Entering state 'left-done'")
    elif upright(x, y, z):
        if state != "upright":
            hold_end = None
            state = "upright"
            print("Entering state 'upright'")
