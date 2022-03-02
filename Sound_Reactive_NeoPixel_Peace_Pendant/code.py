# SPDX-FileCopyrightText: 2017 Limor Fried for Adafruit Industries
#
# SPDX-License-Identifier: MIT

import array
from rainbowio import colorwheel
import board
import neopixel
from analogio import AnalogIn

led_pin = board.D0  # NeoPixel LED strand is connected to GPIO #0 / D0
n_pixels = 12  # Number of pixels you are using
dc_offset = 0  # DC offset in mic signal - if unusure, leave 0
noise = 100  # Noise/hum/interference in mic signal
samples = 60  # Length of buffer for dynamic level adjustment
top = n_pixels + 1  # Allow dot to go slightly off scale

peak = 0  # Used for falling dot
dot_count = 0  # Frame counter for delaying dot-falling speed
vol_count = 0  # Frame counter for storing past volume data

lvl = 10  # Current "dampened" audio level
min_level_avg = 0  # For dynamic adjustment of graph low & high
max_level_avg = 512

# Collection of prior volume samples
vol = array.array('H', [0] * samples)

mic_pin = AnalogIn(board.A1)

strip = neopixel.NeoPixel(led_pin, n_pixels, brightness=.1, auto_write=True)


def remap_range(value, leftMin, leftMax, rightMin, rightMax):
    # this remaps a value from original (left) range to new (right) range
    # Figure out how 'wide' each range is
    leftSpan = leftMax - leftMin
    rightSpan = rightMax - rightMin

    # Convert the left range into a 0-1 range (int)
    valueScaled = int(value - leftMin) / int(leftSpan)

    # Convert the 0-1 range into a value in the right range.
    return int(rightMin + (valueScaled * rightSpan))


while True:
    n = int((mic_pin.value / 65536) * 1000)  # 10-bit ADC format
    n = abs(n - 512 - dc_offset)  # Center on zero

    if n >= noise:  # Remove noise/hum
        n = n - noise

    # "Dampened" reading (else looks twitchy) - divide by 8 (2^3)
    lvl = int(((lvl * 7) + n) / 8)

    # Calculate bar height based on dynamic min/max levels (fixed point):
    height = top * (lvl - min_level_avg) / (max_level_avg - min_level_avg)

    # Clip output
    if height < 0:
        height = 0
    elif height > top:
        height = top

    # Keep 'peak' dot at top
    if height > peak:
        peak = height

        # Color pixels based on rainbow gradient
    for i in range(0, len(strip)):
        if i >= height:
            strip[i] = [0, 0, 0]
        else:
            strip[i] = colorwheel(remap_range(i, 0, (n_pixels - 1), 30, 150))

    # Save sample for dynamic leveling
    vol[vol_count] = n

    # Advance/rollover sample counter
    vol_count += 1

    if vol_count >= samples:
        vol_count = 0

        # Get volume range of prior frames
    min_level = vol[0]
    max_level = vol[0]

    for i in range(1, len(vol)):
        if vol[i] < min_level:
            min_level = vol[i]
        elif vol[i] > max_level:
            max_level = vol[i]

    # minlvl and maxlvl indicate the volume range over prior frames, used
    # for vertically scaling the output graph (so it looks interesting
    # regardless of volume level).  If they're too close together though
    # (e.g. at very low volume levels) the graph becomes super coarse
    # and 'jumpy'...so keep some minimum distance between them (this
    # also lets the graph go to zero when no sound is playing):
    if (max_level - min_level) < top:
        max_level = min_level + top

    # Dampen min/max levels - divide by 64 (2^6)
    min_level_avg = (min_level_avg * 63 + min_level) >> 6
    # fake rolling average - divide by 64 (2^6)
    max_level_avg = (max_level_avg * 63 + max_level) >> 6

    print(n)
