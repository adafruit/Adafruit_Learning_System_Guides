import time
from adafruit_circuitplayground.express import cpx


# pylint: disable=redefined-outer-name
def upright(x, y, z):
    return abs(x) < accel_threshold and abs(y) < accel_threshold and abs(9.8 - z) < accel_threshold


def left_side(x, y, z):
    return abs(9.8 - x) < accel_threshold and abs(y) < accel_threshold and abs(z) < accel_threshold
# pylint: enable=redefined-outer-name


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
