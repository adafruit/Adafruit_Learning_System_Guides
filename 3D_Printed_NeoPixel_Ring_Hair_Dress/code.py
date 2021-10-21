# SPDX-FileCopyrightText: 2014 HerrRausB https://github.com/HerrRausB
# SPDX-FileCopyrightText: 2017 Mikey Sklar for Adafruit Industries
#
# SPDX-License-Identifier: LGPL-3.0-or-later
#
# 3D_Printed_NeoPixel_Ring_Hair_Dress.py
#
# this was ported to CircuitPython from the 'Gemma Hoop Animator'
#
# https://github.com/HerrRausB/GemmaHoopAnimator
#
# unless you # don't like the preset animations or find a
# major bug, you don't need tochange anything here
#
import time

import board
import neopixel

try:
    import urandom as random  # for v1.0 API support
except ImportError:
    import random
from analogio import AnalogIn

# available actions
ACT_NOP = 0x00  # all leds off, do nothing
ACT_SIMPLE_RING = 0x01  # all leds on
ACT_CYCLING_RING_ACLK = 0x02  # anti clockwise cycling colors
ACT_CYCLING_RING_CLKW = 0x04  # clockwise cycling colors
ACT_WHEEL_ACLK = 0x08  # anti clockwise spinning wheel
ACT_WHEEL_CLKW = 0x10  # clockwise spinning wheel
ACT_SPARKLING_RING = 0x20  # sparkling effect

numpix = 16  # total number of NeoPixels
pixel_output = board.D0  # pin where NeoPixels are connected
analog_input = board.A0  # needed to seed the random generator
strip = neopixel.NeoPixel(pixel_output, numpix,
                          brightness=.3, auto_write=False)

# available color generation methods
COL_RANDOM = 0x40  # colors will be generated randomly
COL_SPECTRUM = 0x80  # colors will be set as cyclic spectral wipe

# specifiyng the action list
# the action's overall duration in milliseconds (be careful not
action_duration = 0
# to use values > 2^16-1 - roughly one minute :-)

action_and_color_gen = 1  # the color generation method

# the duration of each action step rsp. the delay of the main
action_step_duration = 2
# loop in milliseconds - thus, controls the action speed (be
# careful not to use values > 2^16-1 - roughly one minute :-)

color_granularity = 3  # controls the increment of the R, G, and B
# portions of the rsp. color. 1 means the increment is 0,1,2,3,...,
# 10 means the increment is 0,10,20,... don't use values > 255, and
# note that even values > 127 wouldn't make much sense...

# controls the speed of color changing independently from action
color_interval = 4

# general global variables
color = 0
color_timer = 0
action_timer = 0
action_step_timer = 0
color_idx = 0
curr_color_interval = 0
curr_action_step_duration = 0
curr_action_duration = 0
curr_action = 0
curr_color_gen = COL_RANDOM
idx = 0
offset = 0
number_of_actions = 31
curr_action_idx = 0
curr_color_granularity = 1
spectrum_part = 0

# defining the animation actions by simply initializing the array of actions
# this array variable must be called theactionlist !!!
#
# valid actions are:
#      ACT_NOP                  simply do nothing and switch everything off
#      ACT_SIMPLE_RING          all leds on
#      ACT_CYCLING_RING_ACLK    anti clockwise cycling colors
#      ACT_CYCLING_RING_CLKW    clockwise cycling colors acording
#      ACT_WHEEL_ACLK           anti clockwise spinning wheel
#      ACT_WHEEL_CLKW           clockwise spinning wheel
#      ACT_SPARKLING_RING       sparkling effect
#
#   valid color options are:
#      COL_RANDOM               colors will be selected randomly, which might
#                               be not very sufficient due to well known
#                               limitations of the random generation algorithm
#      COL_SPECTRUM             colors will be set as cyclic spectral wipe
#                               R -> G -> B -> R -> G -> B -> R -> ...

# action    action name &             action step    color        color change
# duration  color generation method   duration       granularity  interval
theactionlist = [
    [5, ACT_SPARKLING_RING | COL_RANDOM, 0.01, 25, 1],
    [2, ACT_CYCLING_RING_CLKW | COL_RANDOM,
     0.02, 1, 0.005],
    [5, ACT_SPARKLING_RING | COL_RANDOM, 0.01, 25, 1],
    [2, ACT_CYCLING_RING_ACLK | COL_RANDOM,
     0.02, 1, 0.005],
    [5, ACT_SPARKLING_RING | COL_RANDOM, 0.01, 25, 1],
    [2.5, ACT_CYCLING_RING_CLKW | COL_SPECTRUM,
     0.25, 20, 0.020],
    [1, ACT_CYCLING_RING_CLKW | COL_SPECTRUM,
     0.50, 1, 0.020],
    [.750, ACT_CYCLING_RING_CLKW | COL_SPECTRUM,
     0.075, 1, 0.020],
    [.500, ACT_CYCLING_RING_CLKW | COL_SPECTRUM,
     0.100, 1, 0.020],
    [.500, ACT_CYCLING_RING_CLKW | COL_SPECTRUM,
     0.125, 1, 0.020],
    [.500, ACT_CYCLING_RING_CLKW | COL_SPECTRUM,
     0.150, 1, 0.050],
    [.500, ACT_CYCLING_RING_CLKW | COL_SPECTRUM,
     0.175, 1, 0.100],
    [.500, ACT_CYCLING_RING_CLKW | COL_SPECTRUM,
     0.200, 1, 0.200],
    [.750, ACT_CYCLING_RING_CLKW | COL_SPECTRUM,
     0.225, 1, 0.250],
    [1, ACT_CYCLING_RING_CLKW | COL_SPECTRUM,
     0.250, 1, 0.350],
    [30, ACT_SIMPLE_RING | COL_SPECTRUM,
     0.050, 1, 0.010],
    [2.5, ACT_WHEEL_ACLK | COL_SPECTRUM,
     0.010, 1, 0.010],
    [2.5, ACT_WHEEL_ACLK | COL_SPECTRUM,
     0.015, 1, 0.020],
    [2, ACT_WHEEL_ACLK | COL_SPECTRUM,
     0.025, 1, 0.030],
    [1, ACT_WHEEL_ACLK | COL_SPECTRUM,
     0.050, 1, 0.040],
    [1, ACT_WHEEL_ACLK | COL_SPECTRUM,
     0.075, 1, 0.040],
    [1, ACT_WHEEL_ACLK | COL_SPECTRUM,
     0.100, 1, 0.050],
    [.500, ACT_WHEEL_ACLK | COL_SPECTRUM,
     0.125, 1, 0.060],
    [.500, ACT_WHEEL_CLKW | COL_SPECTRUM,
     0.125, 5, 0.050],
    [1, ACT_WHEEL_CLKW | COL_SPECTRUM,
     0.100, 10, 0.040],
    [1.5, ACT_WHEEL_CLKW | COL_SPECTRUM,
     0.075, 15, 0.030],
    [2, ACT_WHEEL_CLKW | COL_SPECTRUM,
     0.050, 20, 0.020],
    [2.5, ACT_WHEEL_CLKW | COL_SPECTRUM,
     0.025, 25, 0.010],
    [3, ACT_WHEEL_CLKW | COL_SPECTRUM,
     0.010, 30, 0.005],
    [5, ACT_SPARKLING_RING | COL_RANDOM, 0.010, 25, 1],
    [5, ACT_NOP, 0, 0, 0]
]

# pylint: disable=global-statement
def nextspectrumcolor():
    global spectrum_part, color_idx, curr_color_granularity, color

    # spectral wipe from green to red
    if spectrum_part == 2:
        color = (color_idx, 0, 255-color_idx)
        color_idx += curr_color_granularity
        if color_idx > 255:
            spectrum_part = 0
            color_idx = 0

    # spectral wipe from blue to green
    elif spectrum_part == 1:
        color = (0, 255 - color_idx, color_idx)
        color_idx += curr_color_granularity
        if color_idx > 255:
            spectrum_part = 2
            color_idx = 0

    # spectral wipe from red to blue
    elif spectrum_part == 0:
        color = (255 - color_idx, color_idx, 0)
        color_idx += curr_color_granularity
        if color_idx > 255:
            spectrum_part = 1
            color_idx = 0


def nextrandomcolor():
    global color

    # granularity = 1 --> [0 .. 255] * 1 --> 0,1,2,3 ... 255
    # granularity = 10 --> [0 .. 25] * 10 --> 0,10,20,30 ... 250
    # granularity = 100 --> [0 .. 2] * 100 --> 0,100, 200 (boaring...)
    random_red = random.randint(0, int(256 / curr_color_granularity))
    random_red *= curr_color_granularity

    random_green = random.randint(0, int(256 / curr_color_granularity))
    random_green *= curr_color_granularity

    random_blue = random.randint(0, int(256 / curr_color_granularity))
    random_blue *= curr_color_granularity

    color = (random_red, random_green, random_blue)


def nextcolor():
    # save some RAM for more animation actions
    if curr_color_gen & COL_RANDOM:
        nextrandomcolor()
    else:
        nextspectrumcolor()


def setup():
    # fingers corssed, the seeding makes sense to really get random colors...
    apin = AnalogIn(analog_input)
    random.seed(apin.value)
    apin.deinit()

    # let's go!
    nextcolor()
    strip.write()


setup()

while True:  # Loop forever...

    # do we need to load the next action?
    if (time.monotonic() - action_timer) > curr_action_duration:
        current_action = theactionlist[curr_action_idx]

        curr_action_duration = current_action[action_duration]
        curr_action = current_action[action_and_color_gen] & 0x3F
        curr_action_step_duration = current_action[action_step_duration]
        curr_color_gen = current_action[action_and_color_gen] & 0xC0
        curr_color_granularity = current_action[color_granularity]
        curr_color_interval = current_action[color_interval]
        curr_action_idx += 1

        # take care to rotate the action list!
        curr_action_idx %= number_of_actions
        action_timer = time.monotonic()

    # do we need to change to the next color?
    if (time.monotonic() - color_timer) > curr_color_interval:
        nextcolor()
        color_timer = time.monotonic()

    # do we need to step up the current action?
    if (time.monotonic() - action_step_timer) > curr_action_step_duration:

        if curr_action:

            is_act_cycling = (ACT_CYCLING_RING_ACLK or ACT_CYCLING_RING_CLKW)

            if curr_action == ACT_NOP:
                # rather trivial even tho this will be repeated as long as the
                # NOP continues - i could have prevented it from repeating
                # unnecessarily, but that would mean more code and less
                # space for more actions within the animation
                for i in range(0, numpix):
                    strip[i] = (0, 0, 0)

            elif curr_action == ACT_SIMPLE_RING:
                # even more trivial - just set the new color, if there is one
                for i in range(0, numpix):
                    strip[i] = color

            elif curr_action == is_act_cycling:
                # spin the ring clockwise or anti clockwise
                if curr_action == ACT_CYCLING_RING_ACLK:
                    idx += 1
                else:
                    idx -= 1

                # prevent overflows or underflows
                idx %= numpix

                # set the new color, if there is one
                strip[idx] = color

            elif curr_action == ACT_WHEEL_ACLK or ACT_WHEEL_CLKW:
                # switch on / off the appropriate pixels according to
                # the current offset
                for idx in range(0, numpix):
                    if ((offset + idx) & 7) < 2:
                        strip[idx] = color
                    else:
                        strip[idx] = (0, 0, 0)

                # advance the offset and thus, spin the wheel
                if curr_action == ACT_WHEEL_CLKW:
                    offset += 1
                else:
                    offset -= 1

                # prevent overflows or underflows
                offset %= numpix

            elif curr_action == ACT_SPARKLING_RING:
                # switch current pixel off
                strip[idx] = (0, 0, 0)
                # pick a new pixel
                idx = random.randint(0, numpix)
                # set new pixel to the current color
                strip[idx] = color

        strip.write()
        action_step_timer = time.monotonic()
