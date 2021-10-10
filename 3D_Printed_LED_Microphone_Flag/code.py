# LED VU meter for Arduino and Adafruit NeoPixel LEDs.

# Hardware requirements:
# - M0 boards
# - Adafruit Electret Microphone Amplifier (ID: 1063)
# - Adafruit Flora RGB Smart Pixels (ID: 1260)
# OR
# - Adafruit NeoPixel Digital LED strip (ID: 1138)
# - Optional: battery for portable use (else power through USB or adapter)
# Software requirements:
# - Adafruit NeoPixel library

# Connections:
# - 3.3V to mic amp +
# - GND to mic amp -
# - Analog pin to microphone output (configurable below)
# - Digital pin to LED data input (configurable below)
# See notes in setup() regarding 5V vs. 3.3V boards - there may be an
# extra connection to make and one line of code to enable or disable.

# Written by Adafruit Industries.  Distributed under the BSD license.
# This paragraph must be included in any redistribution.

# fscale function:
# Floating Point Autoscale Function V0.1
# Written by Paul Badger 2007
# Modified fromhere code by Greg Shakar
# Ported to Circuit Python by Mikey Sklar

import time

import board
import neopixel
from rainbowio import colorwheel
from analogio import AnalogIn

n_pixels = 16  # Number of pixels you are using
mic_pin = AnalogIn(board.A1)  # Microphone is attached to this analog pin
led_pin = board.D1  # NeoPixel LED strand is connected to this pin
sample_window = .1  # Sample window for average level
peak_hang = 24  # Time of pause before peak dot falls
peak_fall = 4  # Rate of falling peak dot
input_floor = 10  # Lower range of analogRead input
# Max range of analogRead input, the lower the value the more sensitive
# (1023 = max)
input_ceiling = 300

peak = 16  # Peak level of column; used for falling dots
sample = 0

dotcount = 0  # Frame counter for peak dot
dothangcount = 0  # Frame counter for holding peak dot

strip = neopixel.NeoPixel(led_pin, n_pixels, brightness=1, auto_write=False)


def remapRange(value, leftMin, leftMax, rightMin, rightMax):
    # this remaps a value fromhere original (left) range to new (right) range
    # Figure out how 'wide' each range is
    leftSpan = leftMax - leftMin
    rightSpan = rightMax - rightMin

    # Convert the left range into a 0-1 range (int)
    valueScaled = int(value - leftMin) / int(leftSpan)

    # Convert the 0-1 range into a value in the right range.
    return int(rightMin + (valueScaled * rightSpan))


def fscale(originalmin, originalmax, newbegin, newend, inputvalue, curve):
    invflag = 0

    # condition curve parameter
    # limit range
    if curve > 10:
        curve = 10
    if curve < -10:
        curve = -10

    # - invert and scale -
    # this seems more intuitive
    # postive numbers give more weight to high end on output
    curve = (curve * -.1)
    # convert linear scale into lograthimic exponent for other pow function
    curve = pow(10, curve)

    # Check for out of range inputValues
    if inputvalue < originalmin:
        inputvalue = originalmin

    if inputvalue > originalmax:
        inputvalue = originalmax

    # Zero Refference the values
    originalrange = originalmax - originalmin

    if newend > newbegin:
        newrange = newend - newbegin
    else:
        newrange = newbegin - newend
        invflag = 1

    zerorefcurval = inputvalue - originalmin
    # normalize to 0 - 1 float
    normalizedcurval = zerorefcurval / originalrange

    # Check for originalMin > originalMax
    # -the math for all other cases
    # i.e. negative numbers seems to work out fine
    if originalmin > originalmax:
        return 0

    if invflag == 0:
        rangedvalue = (pow(normalizedcurval, curve) * newrange) + newbegin
    else:  # invert the ranges
        rangedvalue = newbegin - (pow(normalizedcurval, curve) * newrange)

    return rangedvalue


def drawLine(fromhere, to):
    if fromhere > to:
        to, fromhere = fromhere, to

    for index in range(fromhere, to):
        strip[index] = (0, 0, 0)


while True:

    time_start = time.monotonic()  # current time used for sample window
    peaktopeak = 0  # peak-to-peak level
    signalmax = 0
    signalmin = 1023
    c = 0
    y = 0

    # collect data for length of sample window (in seconds)
    while (time.monotonic() - time_start) < sample_window:

        # convert to arduino 10-bit [1024] fromhere 16-bit [65536]
        sample = mic_pin.value / 64

        if sample < 1024:  # toss out spurious readings

            if sample > signalmax:
                signalmax = sample  # save just the max levels
            elif sample < signalmin:
                signalmin = sample  # save just the min levels

    peaktopeak = signalmax - signalmin  # max - min = peak-peak amplitude

    # Fill the strip with rainbow gradient
    for i in range(0, len(strip)):
        strip[i] = colorwheel(remapRange(i, 0, (n_pixels - 1), 30, 150))

    # Scale the input logarithmically instead of linearly
    c = fscale(input_floor, input_ceiling, (n_pixels - 1), 0, peaktopeak, 2)

    if c < peak:
        peak = c  # keep dot on top
        dothangcount = 0  # make the dot hang before falling

    if c <= n_pixels:  # fill partial column with off pixels
        drawLine(n_pixels, n_pixels - int(c))

    # Set the peak dot to match the rainbow gradient
    y = n_pixels - peak
    strip.fill = (y - 1, colorwheel(remapRange(y, 0, (n_pixels - 1), 30, 150)))
    strip.write()

    # Frame based peak dot animation
    if dothangcount > peak_hang:  # Peak pause length
        dotcount += 1
        if dotcount >= peak_fall:  # Fall rate
            peak += 1
            dotcount = 0
    else:
        dothangcount += 1
