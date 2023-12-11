# SPDX-FileCopyrightText: 2020 Kattni Rembor for Adafruit Industries
#
# SPDX-License-Identifier: MIT

import time
import board
import adafruit_lis3dh
import neopixel

# The interval you would like to be reminded to drink water, in minutes.
hydration_reminder = 60

# Length of time, in minutes, before timer begins Red Alert blinking.
red_alert_delay = 2

# The color will fade from color_begin to color_complete. This is a gentle indicator of how much
# time has passed. Set to any two colors.
color_begin = (0, 0, 255)  # Blue. Set to any color to begin your countdown.
color_complete = (255, 255, 255)  # White. Set to any color to end your countdown.
led_brightness = 0.2  # Set to a number between 0.0 and 1.0 to set LED brightness.

# Increase or decrease this to change the speed of the Red Alert blinking in seconds.
red_alert_blink_speed = 0.5

# These are the thresholds the z-axis values must exceed for the orientation to be considered
# "up" or "down". These values are valid if the LIS3DH breakout is mounted horizontally inside the
# timer assembly. If you want the option to have the timer on an angle while timing, you can
# calibrate these values by uncommenting the print(z) in orientation() to see the z-axis values and
# update the thresholds to match the desired range.
down_threshold = -8
up_threshold = 8

# Number of LEDs. Default is 32 (2 x rings of 16 each). If you use a different form of NeoPixels,
# update this to match the total number of pixels.
number_of_pixels = 32

# Set up accelerometer and LEDs.
i2c = board.I2C()  # uses board.SCL and board.SDA
# i2c = board.STEMMA_I2C()  # For using the built-in STEMMA QT connector on a microcontroller
lis3dh = adafruit_lis3dh.LIS3DH_I2C(i2c)
pixels = neopixel.NeoPixel(board.A3, number_of_pixels, brightness=led_brightness)
pixels.fill(0)  # Turn off the LEDs if they're on.

STATE_IDLE = "Idle"
STATE_TIMING = "Timing"
STATE_TIMING_COMPLETE = "Timing complete"
RED_ALERT = "Red Alert"


def gradient(color_one, color_two, blend_weight):
    """
    Blend between two colors with a given ratio.

    :param color_one:  first color, as an (r,g,b) tuple
    :param color_two:  second color, as an (r,g,b) tuple
    :param blend_weight: Blend weight (ratio) of second color, 0.0 to 1.0
    """
    if blend_weight < 0.0:
        blend_weight = 0.0
    elif blend_weight > 1.0:
        blend_weight = 1.0
    initial_weight = 1.0 - blend_weight
    return (int(color_one[0] * initial_weight + color_two[0] * blend_weight),
            int(color_one[1] * initial_weight + color_two[1] * blend_weight),
            int(color_one[2] * initial_weight + color_two[2] * blend_weight))


# pylint: disable=global-statement
def set_state(state):
    global current_state, state_changed
    current_state = state
    state_changed = time.monotonic()
    print("Current state:", current_state)  # Print the current state.


def orientation():
    """Determines orientation based on z-axis values. Thresholds set above."""
    _, _, z = lis3dh.acceleration
    # print(z)  # Uncomment to print the z-axis value. Use to calibrate thresholds if desired.
    if z < down_threshold:
        return 'down'
    if z > up_threshold:
        return 'up'
    return 'side'


def orientation_debounced():
    """
    Debounces the orientation changes. For a new orientation to be registered, the timer must
    be in that orientation for the duration of the delay.
    """
    delay = 0.2
    initial_time = time.monotonic()
    initial_orientation = orientation()
    while True:
        new_orientation = orientation()
        if new_orientation != initial_orientation:
            initial_time = time.monotonic()
            initial_orientation = new_orientation
            continue
        if time.monotonic() - initial_time > delay:
            return new_orientation


def state_from_orientation():
    """Determines the state based on orientation."""
    global current_orientation
    new_orientation = orientation_debounced()
    if new_orientation != current_orientation:
        if new_orientation == 'side':
            set_state(STATE_IDLE)
            current_orientation = orientation_debounced()
            return
        set_state(STATE_TIMING)
        current_orientation = orientation_debounced()


def idle():
    """The idle state."""
    pixels.fill(0)
    state_from_orientation()


def timing():
    """The timing active state."""
    state_from_orientation()

    activity_duration = hydration_reminder * 60  # Converts minutes to seconds.

    elapsed = time.monotonic() - state_changed

    if elapsed >= activity_duration:
        set_state(STATE_TIMING_COMPLETE)
        return

    blend = (elapsed / activity_duration)
    pixels.fill(gradient(color_begin, color_complete, blend))


def timing_complete():
    """The timing complete state."""
    pixels.fill(color_complete)

    state_from_orientation()

    elapsed = time.monotonic() - state_changed

    if elapsed >= (red_alert_delay * 60):  # Converts minutes to seconds.
        set_state(RED_ALERT)
        return


blink_is_on = False


def red_alert():
    """The Red Alert state."""
    global blink_is_on
    elapsed = time.monotonic() - state_changed
    if elapsed >= red_alert_blink_speed:
        set_state(RED_ALERT)
        blink_is_on = not blink_is_on
    if blink_is_on:
        pixels.fill(color_complete)
    else:
        pixels.fill(0)

    state_from_orientation()


current_orientation = orientation_debounced()  # Get the initial orientation.
state_changed = time.monotonic()  # Set an initial timestamp.
current_state = STATE_IDLE  # Set initial state to idle.

print("Start state:", current_state)  # Print the starting state.

while True:
    if current_state == STATE_IDLE:
        idle()
    if current_state == STATE_TIMING:
        timing()
    if current_state == STATE_TIMING_COMPLETE:
        timing_complete()
    if current_state == RED_ALERT:
        red_alert()
