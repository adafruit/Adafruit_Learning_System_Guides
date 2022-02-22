# SPDX-FileCopyrightText: 2018 Tony DiCola for Adafruit Industries
#
# SPDX-License-Identifier: MIT

# Cyber Flower: Digital Valentine
#
# 'Roses are red,
#  Violets are blue,
#  This flower changes color,
#  To show its love for you.'
#
# Load this on a Gemma M0 running CircuitPython and it will smoothly animate
# the DotStar LED between different color hues.  Touch the D0 pad and it will
# cause the pixel to pulse like a heart beat.  You might need to also attach a
# wire to the ground pin to ensure capacitive touch sensing can work on battery
# power.  For example strip the insulation from a wire and solder it to ground,
# then solder a wire (with the insulation still attached) to D0, and wrap
# both wires around the stem of a flower like a double-helix.  When you touch
# the wires you'll ground yourself (touching the bare ground wire) and cause
# enough capacitance in the D0 wire (even though it's still insulated) to
# trigger the heartbeat.  Or just leave D0 unconnected to have a nicely
# animated lit-up flower!
#
# Note that on power-up the flower will wait about 5 seconds before turning on
# the LED.  During this time the board's red LED will flash and this is an
# indication that it's waiting to power on.  Place the flower down so nothing
# is touching it and then pick it up again after the DotStar LED starts
# animating.  This will ensure the capacitive touch sensing isn't accidentally
# calibrated with your body touching it (making it less accurate).
#
# Author: Tony DiCola
# License: MIT License
import math
import time

import board
import busio
import digitalio
import touchio

# Variables that control the code.  Try changing these to modify speed, color,
# etc.
START_DELAY = 5.0  # How many seconds to wait after power up before
# jumping into the animation and initializing the
# touch input.  This gives you time to take move your
# fingers off the flower so the capacitive touch
# sensing is better calibrated.  During the delay
# the small red LED on the board will flash.

TOUCH_PIN = board.D0  # The board pin to listen for touches and trigger the
# heart beat animation.  You can change this to any
# other pin like board.D2 or board.D1.  Make sure not
# to touch this pin as the board powers on or the
# capacitive sensing will get confused (just reset
# the board and try again).

BRIGHTNESS = 1.0  # The brightness of the colors.  Set this to a value
# anywhere within 0 and 1.0, where 1.0 is full bright.
# For example 0.5 would be half brightness.

RAINBOW_PERIOD_S = 18.0  # How many seconds it takes for the default rainbow
# cycle animation to perform a full cycle.  Increase
# this to slow down the animation or decrease to speed
# it up.

HEARTBEAT_BPM = 60.0  # Heartbeat animation beats per minute.  Increase to
# speed up the heartbeat, and decrease to slow down.

HEARTBEAT_HUE = 300.0  # The color hue to use when animating the heartbeat
# animation.  Pick a value in the range of 0 to 359
# degrees, see the hue spectrum here:
#   https://en.wikipedia.org/wiki/Hue
# A value of 300 is a nice pink color.

# First initialize the DotStar LED and turn it off.
# We'll manually drive the dotstar instead of depending on the adafruit_dotstar
# library for simplicity--there's no need to install other dependencies for
# driving this one LED.
dotstar_spi = busio.SPI(clock=board.APA102_SCK, MOSI=board.APA102_MOSI)
# Raw dotstar protocol, start with 4 bytes of zero, then 0xFF and B, G, R
# pixel data, followed by bytes of 0xFF tail (just one for 1 pixel).
dotstar_data = bytearray([0x00, 0x00, 0x00, 0x00, 0xFF, 0x00, 0x00, 0x00,
                          0xFF])


# Define a function to simplify setting dotstar color.


def dotstar_color(rgb_color):
    # Set the color of the dot star LED.  This is barebones dotstar driving
    # code for simplicity and less dependency on other libraries.  We're only
    # driving one LED!
    try:
        while not dotstar_spi.try_lock():
            pass
        dotstar_spi.configure(baudrate=4000000)
        dotstar_data[5] = rgb_color[2] & 0xFF  # Blue
        dotstar_data[6] = rgb_color[1] & 0xFF  # Green
        dotstar_data[7] = rgb_color[0] & 0xFF  # Red
        dotstar_spi.write(dotstar_data)
    finally:
        dotstar_spi.unlock()


# Call the function above to turn off the dotstar initially (set it to all 0).
dotstar_color((0, 0, 0))

# Also make sure the on-board red LED is turned off.
red_led = digitalio.DigitalInOut(board.L)
red_led.switch_to_output(value=False)

# Wait the startup delay period while flashing the red LED.  This gives time
# to move your hand away from the flower/stem so the capacitive touch sensing
# is initialized and calibrated with a good non-touch starting state.
start = time.monotonic()
while time.monotonic() - start <= START_DELAY:
    # Blink the red LED on and off every half second.
    red_led.value = True
    time.sleep(0.5)
    red_led.value = False
    time.sleep(0.5)

# Setup the touch input.
touch = touchio.TouchIn(TOUCH_PIN)

# Convert periods to frequencies that are used later in animations.
rainbow_freq = 1.0 / RAINBOW_PERIOD_S

# Calculcate periods and values used by the heartbeat animation.
beat_period = 60.0 / HEARTBEAT_BPM
beat_quarter_period = beat_period / 4.0  # Quarter period controls the speed of
# the heartbeat drop-off (using an
# exponential decay function).
beat_phase = beat_period / 5.0  # Phase controls how long in-between
# the two parts of the heart beat
# (the 'ba-boom' of the beat).

# pylint: disable=redefined-outer-name
# Define a gamma correction lookup table to make colors more accurate.
# See this guide for more background on gamma correction:
#   https://learn.adafruit.com/led-tricks-gamma-correction/
gamma8 = bytearray(256)
for i in range(len(gamma8)):
    gamma8[i] = int(math.pow(i / 255.0, 2.8) * 255.0 + 0.5) & 0xFF


# Define a function to convert from HSV (hue, saturation, value) color to
# RGB colors that DotStar LEDs speak.  The HSV color space is a nicer for
# animations because you can easily change the hue and value (brightness)
# vs. RGB colors.  Pass in a hue (in degrees from 0-360) and saturation and
# value that range from 0 to 1.0.  This will also use the gamma correction
# table above to get the most accurate color.  Adapted from C/C++ code here:
#   https://www.cs.rit.edu/~ncs/color/t_convert.html


def HSV_to_RGB(h, s, v):
    if s == 0.0:
        r = v
        g = v
        b = v
    else:
        h /= 60.0  # sector 0 to 5
        i = int(math.floor(h))
        f = h - i  # factorial part of h
        p = v * (1.0 - s)
        q = v * (1.0 - s * f)
        t = v * (1.0 - s * (1.0 - f))
        if i == 0:
            r = v
            g = t
            b = p
        elif i == 1:
            r = q
            g = v
            b = p
        elif i == 2:
            r = p
            g = v
            b = t
        elif i == 3:
            r = p
            g = q
            b = v
        elif i == 4:
            r = t
            g = p
            b = v
        else:
            r = v
            g = p
            b = q
    r = gamma8[int(255.0 * r)]
    g = gamma8[int(255.0 * g)]
    b = gamma8[int(255.0 * b)]
    return (r, g, b)


# Another handy function for linear interpolation of a value.  Pass in a value
# x that's within the range x0...x1 and a range y0...y1 to get an output value
# y that's proportionally within y0...y1 based on x within x0...x1.  Handy for
# transforming a value in one range to a value in another (like Arduino's map
# function).


def lerp(x, x0, x1, y0, y1):
    return y0 + (x - x0) * ((y1 - y0) / (x1 - x0))


# Main loop below will run forever:
while True:
    # Get the current time at the start of the animation update.
    current = time.monotonic()
    # Now check if the touch input is being touched and choose a different
    # animation to run, either a rainbow cycle or heartbeat.
    if touch.value:
        # The touch input is being touched, so figure out the color using
        # a heartbeat animation.
        # This works using exponential decay of the color value (brightness)
        # over time:
        #   https://en.wikipedia.org/wiki/Exponential_decay
        # A heart beat is made of two sub-beats (the 'ba-boom') so two decay
        # functions are calculated using the same fall-off period but slightly
        # out of phase so one occurs a little bit after the other.
        t0 = current % beat_period
        t1 = (current + beat_phase) % beat_period
        x0 = math.pow(math.e, -t0 / beat_quarter_period)
        x1 = math.pow(math.e, -t1 / beat_quarter_period)
        # After calculating both exponential decay values pick the biggest one
        # as the secondary one will occur after the first.  Scale each by
        # the global brightness and then convert to RGB color using the fixed
        # hue but modulating the color value (brightness).  Luckily the result
        # of the exponential decay is a value that goes from 1.0 to 0.0 just
        # like we expect for full bright to zero brightness with HSV color
        # (i.e. no interpolation is necessary).
        val = max(x0, x1) * BRIGHTNESS
        dotstar_color(HSV_to_RGB(HEARTBEAT_HUE, 1.0, val))
    else:
        # The touch input is not being touched (touch.value is False) so
        # compute the hue with a smooth cycle over time.
        # First use the sine function to smoothly generate a value that goes
        # from -1.0 to 1.0 at a certain frequency to match the rainbow period.
        x = math.sin(2.0 * math.pi * rainbow_freq * current)
        # Then compute the hue by converting the sine wave value from something
        # that goes from -1.0 to 1.0 to instead go from 0 to 359 degrees.
        hue = lerp(x, -1.0, 1.0, 0.0, 359.0)
        # Finally update the DotStar LED by converting the HSV color at the
        # specified hue to a RGB color the LED understands.
        dotstar_color(HSV_to_RGB(hue, 1.0, BRIGHTNESS))
