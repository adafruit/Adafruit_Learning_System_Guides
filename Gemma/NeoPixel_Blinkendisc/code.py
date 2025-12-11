# SPDX-FileCopyrightText: 2017 Phillip Burgess for Adafruit Industries
#
# SPDX-License-Identifier: MIT

import time

import analogio
import board
import digitalio
import neopixel

try:
    import urandom as random  # for v1.0 API support
except ImportError:
    import random

num_leds = 24  # 24 LED NeoPixel ring
neopixel_pin = board.D0  # Pin where NeoPixels are connected
vibration_pin = board.D1  # Pin where vibration switch is connected
analog_pin = board.A0  # Not connected to anything
strip = neopixel.NeoPixel(neopixel_pin, num_leds)

default_frame_len = 0.06  # Time (in seconds) of typical animation frame
max_frame_len = 0.25  # Gradually slows toward this
min_frame_len = 0.005  # But sometimes as little as this
cooldown_at = 2.0  # After this many seconds, start slowing down
dim_at = 2.5  # After this many seconds, dim LEDs
brightness_high = 0.5  # Active brightness
brightness_low = 0.125  # Idle brightness

color = [0, 120, 30]  # Initial LED color
offset = 0  # Animation position
frame_len = default_frame_len  # Frame-to-frame time, seconds
last_vibration = 0.0  # Time of last vibration
last_frame = 0.0  # Time of last animation frame

# Random number generator is seeded from an unused 'floating'
# analog input - this helps ensure the random color choices
# aren't always the same order.
pin = analogio.AnalogIn(analog_pin)
random.seed(pin.value)
pin.deinit()

# Set up digital pin for reading vibration switch
pin = digitalio.DigitalInOut(vibration_pin)
pin.direction = digitalio.Direction.INPUT
pin.pull = digitalio.Pull.UP

while True:  # Loop forever...

    while True:
        # Compare time.monotonic() against last_frame to keep
        # frame-to-frame animation timing consistent.  Use this
        # idle time to check the vibration switch for activity.
        t = time.monotonic()
        if t - last_frame >= frame_len:
            break
        if not pin.value:  # Vibration switch activated?
            color = [  # Pick a random RGB color...
                random.randint(32, 255),
                random.randint(32, 255),
                random.randint(32, 255)]
            frame_len = default_frame_len  # Reset frame timing
            last_vibration = t  # Save last trigger time

    # Stretch out frames if nothing has happened in a couple of seconds:
    if (t - last_vibration) > cooldown_at:
        frame_len += 0.001  # Add 1 ms
        if frame_len > max_frame_len:
            frame_len = min_frame_len

    # If we haven't registered a vibration in dim_at ms, go dim:
    if (t - last_vibration) > dim_at:
        strip.brightness = brightness_low
    else:
        strip.brightness = brightness_high

    # Erase previous pixels and light new ones:
    strip.fill([0, 0, 0])
    for i in range(0, num_leds, 6):
        strip[(offset + i) % num_leds] = color

    strip.write()  # and issue data to LED strip

    # Increase pixel offset until it hits 6, then roll back to 0:
    offset = (offset + 1) % 6

    last_frame = t
