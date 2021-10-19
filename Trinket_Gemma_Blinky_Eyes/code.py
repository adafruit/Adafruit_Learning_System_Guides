# SPDX-FileCopyrightText: 2018 Mikey Sklar for Adafruit Industries
#
# SPDX-License-Identifier: GPLv3

"""
Blinking Eyes - based on code by Brad Blumenthal, MAKE Magazine
License: GPLv3
"""

import time

import analogio
import board
import pwmio

try:
    import urandom as random  # for v1.0 API support
except ImportError:
    import random

# Initialize photocell
photocell_pin = board.A1  # cds photocell connected to this ANALOG pin
darkness_max = (2 ** 16 / 2)  # more dark than light > 32k out of 64k
photocell = analogio.AnalogIn(photocell_pin)

# Initialize PWM
# PWM (fading) - Both LEDs are connected on D0
# (PWM not avail on D1)
pwm_leds = board.D0
pwm = pwmio.PWMOut(pwm_leds, frequency=1000, duty_cycle=0)
brightness = 0  # how bright the LED is
fade_amount = 1285  # 2% steping of 2^16
counter = 0  # counter to keep track of cycles

# blink delay
blink_delay = True
blink_freq_min = 3
blink_freq_max = 6

# Loop forever...
while True:

    # turn on LEDs if it is dark out
    if photocell.value < darkness_max:

        # blink frequency and timer
        if blink_delay:
            blink_delay = False
            blink_timer_start = time.monotonic()
            blink_freq = random.randint(blink_freq_min, blink_freq_max)

        # time to blink? Blink once every 3 - 6 seconds (random assingment)
        if (time.monotonic() - blink_timer_start) >= blink_freq:
            blink_delay = True
            pwm.duty_cycle = 0
            time.sleep(.1)

        # send to LED as PWM level
        pwm.duty_cycle = brightness

        # change the brightness for next time through the loop:
        brightness = brightness + fade_amount

        # reverse the direction of the fading at the ends of the fade:
        if brightness <= 0:
            fade_amount = -fade_amount
            counter += 1
        elif brightness >= 65535:
            fade_amount = -fade_amount
            counter += 1

        # wait for 15 ms to see the dimming effect
        time.sleep(.015)

    else:

        # shutoff LEDs, it is too bright
        pwm.duty_cycle = 0
