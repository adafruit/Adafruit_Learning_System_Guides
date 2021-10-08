# SPDX-FileCopyrightText: 2021 Phil Burgess for Adafruit Industries
#
# SPDX-License-Identifier: MIT

"""
ACCELEROMETER INPUT DEMO: while the LED Glasses Driver has a perfectly
good clicky button for input, this code shows how one might instead use
the onboard accelerometer for interactions*.

Worn normally, the LED rings are simply lit a solid color.
TAP the eyeglass frames to cycle among a list of available colors.
LOOK DOWN to light the LED rings bright white -- for navigating steps
or finding the right key. LOOK BACK UP to return to solid color.
This uses only the rings, not the matrix portion.

* Like, if you have big ol' monster hands, that little button can be
  hard to click, y'know?
"""

import time
import board
import digitalio
import supervisor
import adafruit_lis3dh
import adafruit_is31fl3741
from adafruit_is31fl3741.adafruit_ledglasses import LED_Glasses

i2c = board.I2C()  # Shared by both the accelerometer and LED controller

# Initialize the accelerometer and enable single-tap detection
int1 = digitalio.DigitalInOut(board.ACCELEROMETER_INTERRUPT)
lis3dh = adafruit_lis3dh.LIS3DH_I2C(i2c, int1=int1)
lis3dh.set_tap(1, 100)
last_tap_time = 0

# Initialize the IS31 LED driver, buffered for smoother animation
glasses = LED_Glasses(i2c, allocate=adafruit_is31fl3741.MUST_BUFFER)

# Here's a list of colors that we cycle through when tapped, specified
# as (R,G,B) tuples from 0-255. These are intentionally a bit dim --
# both to save battery and to make the "ground light" mode more dramatic.
# Rather than primary color red/green/blue sequence which is just so
# over-done at this point, let's use some HALLOWEEN colors!
colors = ((27, 9, 0), (12, 0, 24), (5, 31, 0))  # Orange, purple, green
color_index = 0  # Begin at first color in list

# Check accelerometer to see if we've started in the looking-down state,
# set the target color (what we're aiming for) appropriately. Only the
# Y axis is needed for this.
_, filtered_y, _ = lis3dh.acceleration
looking_down = filtered_y > 5
target_color = (255, 255, 255) if looking_down else colors[color_index]

interpolated_color = (0, 0, 0)  # LEDs off at startup, they'll ramp up


while True:  # Loop forever...

    # The try/except here is because VERY INFREQUENTLY the I2C bus will
    # encounter an error when accessing either the accelerometer or the
    # LED driver, whether from bumping around the wires or sometimes an
    # I2C device just gets wedged. To more robustly handle the latter,
    # the code will restart if that happens.
    try:

        # interpolated_color blends from the prior to the next ("target")
        # LED ring colors, with a pleasant ease-out effect.
        interpolated_color = (
            interpolated_color[0] * 0.85 + target_color[0] * 0.15,
            interpolated_color[1] * 0.85 + target_color[1] * 0.15,
            interpolated_color[2] * 0.85 + target_color[2] * 0.15,
        )
        # Fill both rings with interpolated_color, then refresh the LEDs.
        # fill_color(interpolated_color)
        packed = (
            (int(interpolated_color[0]) << 16)
            | (int(interpolated_color[1]) << 8)
            | int(interpolated_color[2])
        )
        glasses.left_ring.fill(packed)
        glasses.right_ring.fill(packed)
        glasses.show()

        # The look-down detection only needs the accelerometer's Y axis.
        # This works with the Glasses Driver mounted on either temple and
        # with the glasses arms "open" (as when worn).
        _, y, _ = lis3dh.acceleration
        # Smooth the accelerometer reading the same way RGB colors are
        # interpolated. This avoids false triggers from jostling around.
        filtered_y = filtered_y * 0.85 + y * 0.15
        # The threshold between "looking down" and "looking up" depends
        # on which of those states we're currently in. This is an example
        # of hysteresis in software...a change of direction requires a
        # little extra push before it takes, which avoids oscillating if
        # there was just a single threshold both ways.
        if looking_down:  #             Currently in the looking-down state
            _ = lis3dh.tapped  #        Discard any taps while looking down
            if filtered_y < 3.5:  #     Have we crossed the look-up threshold?
                target_color = colors[color_index]
                looking_down = False  # We're looking up now!
        else:  #                        Currently in looking-up state
            if filtered_y > 5:  #       Crossed the look-down threshold?
                target_color = (255, 255, 255)
                looking_down = True  #  We're looking down now!
            elif lis3dh.tapped:
                # No look up/down change, but the accelerometer registered
                # a tap. Compare this against the last time we sensed one,
                # and only do things if it's been more than half a second.
                # This avoids spurious double-taps that can occur no matter
                # how carefully the tap threshold was set.
                now = time.monotonic()
                elapsed = now - last_tap_time
                if elapsed > 0.5:
                    # A good tap was detected. Cycle to the next color in
                    # the list and note the time of this tap.
                    color_index = (color_index + 1) % len(colors)
                    target_color = colors[color_index]
                    last_tap_time = now

    # See "try" notes above regarding rare I2C errors.
    except OSError:
        supervisor.reload()
