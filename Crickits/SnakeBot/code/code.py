# SPDX-FileCopyrightText: 2018 Dave Astels for Adafruit Industries
#
# SPDX-License-Identifier: MIT

import time
import random
from adafruit_crickit import crickit

LEFT = False
RIGHT = True

random.seed(int(time.monotonic()))
ss = crickit.seesaw

left_wheel = crickit.dc_motor_1
right_wheel = crickit.dc_motor_2

RIGHT_BUMPER = crickit.SIGNAL1
LEFT_BUMPER = crickit.SIGNAL2
CENTER_BUMPER = crickit.SIGNAL3
LBO = crickit.SIGNAL4

ss.pin_mode(RIGHT_BUMPER, ss.INPUT_PULLUP)
ss.pin_mode(LEFT_BUMPER, ss.INPUT_PULLUP)
ss.pin_mode(CENTER_BUMPER, ss.INPUT_PULLUP)
ss.pin_mode(LBO, ss.INPUT_PULLUP)

# These allow easy correction for motor speed variation.
# Factors are determined by observation and fiddling.
# Start with both having a factor of 1.0 (i.e. none) and
# adjust until the bot goes more or less straight
def set_right(speed):
    right_wheel.throttle = speed * 0.9

def set_left(speed):
    left_wheel.throttle = speed


# Uncomment this to find the above factors
# set_right(1.0)
# set_left(1.0)
# while True:
#     pass


# Check for bumper activation and move away accordingly
# Returns False if we got clear, True if we gave up
def react_to_bumpers():
    set_left(0.0)
    set_right(0.0)
    attempt_count = 0

    # keep trying to back away and turn until we're free
    while True:

        # give up after 3 tries
        if attempt_count == 3:
            return True

        bumped_left = not ss.digital_read(LEFT_BUMPER)
        bumped_right = not ss.digital_read(RIGHT_BUMPER)
        bumped_center = not ss.digital_read(CENTER_BUMPER)

        # Didn't bump into anything, we're done here
        if not bumped_left and not bumped_right and not bumped_center:
            return False

        # If the middle bumper was triggered, randomly pick a way to turn
        if bumped_center:
            bumped_left |= random.randrange(10) < 5
            bumped_right = not bumped_left

        # Back away a bit
        set_left(-0.5)
        set_right(-0.5)
        time.sleep(0.5)

        # If we bumped on the left, turn to the right
        if bumped_left:
            set_left(1.0)
            set_right(0.0)

            # If we bumped on the right, turn left
        elif bumped_right:
            set_left(0.0)
            set_right(1.0)

            # time to turn for
        time.sleep(random.choice([0.2, 0.3, 0.4]))
        attempt_count += 1


def tack(direction, duration):
    target_time = time.monotonic() + duration
    if direction == LEFT:
        set_left(0.25)
        set_right(1.0)
    else:
        set_left(1.0)
        set_right(0.25)
    while time.monotonic() < target_time:
        if not(ss.digital_read(LEFT_BUMPER) and
               ss.digital_read(RIGHT_BUMPER) and
               ss.digital_read(CENTER_BUMPER)):
            return react_to_bumpers()
    return False


while True:
    # check for low voltage/stall
    if not ss.digital_read(LBO):
        break
    if tack(LEFT, 0.75):
        break
    if tack(RIGHT, 0.75):
        break

set_left(0)
set_right(0)

while True:
    for _ in range(3):
        crickit.drive_2.fraction = 1.0
        time.sleep(0.1)
        crickit.drive_2.fraction = 0.0
        time.sleep(.2)
    time.sleep(10.0)
