# SPDX-FileCopyrightText: 2018 Kattni Rembor for Adafruit Industries
#
# SPDX-License-Identifier: MIT

from adafruit_circuitplayground.express import cpx

# Set to check for single-taps.
cpx.detect_taps = 1
tap_count = 0

# We're looking for 2 single-taps before moving on.
while tap_count < 2:
    if cpx.tapped:
        print("Single-tap!")
        tap_count += 1
print("Reached 2 single-taps!")

# Now switch to checking for double-taps.
tap_count = 0
cpx.detect_taps = 2

# We're looking for 2 double-taps before moving on.
while tap_count < 2:
    if cpx.tapped:
        print("Double-tap!")
        tap_count += 1

print("Reached 2 double-taps!")
cpx.red_led = True
print("Done.")
