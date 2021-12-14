# SPDX-FileCopyrightText: 2021 Noe Ruiz for Adafruit Industries
#
# SPDX-License-Identifier: MIT

"""
Guardian Egg Shoulder Robot with servo and NeoPixel ring
"""

# pylint: disable=import-error
import time
import random
import board
import pwmio
import neopixel
from adafruit_motor import servo
from adafruit_led_animation.animation.comet import Comet
from adafruit_led_animation.animation.SparklePulse import SparklePulse
from adafruit_led_animation.sequence import AnimationSequence
from adafruit_led_animation.color import RED, BLUE

PIXEL_PIN = board.D5
SERVO_PIN = board.A2
NUM_PIXELS = 12
ORDER = neopixel.GRB
BRIGHTNESS = 0.6

# Initialize servo
PWM = pwmio.PWMOut(SERVO_PIN, frequency=50)
SERVO = servo.Servo(PWM)

# Initialize NeoPixels and animations
PIXELS = neopixel.NeoPixel(PIXEL_PIN, NUM_PIXELS, auto_write=False,
                           pixel_order=ORDER)
LARSON = Comet(PIXELS, bounce=True, speed=0.6/NUM_PIXELS,
               tail_length=NUM_PIXELS//2,
               color=(RED[0] * BRIGHTNESS,  # This is a little faster than
                      RED[1] * BRIGHTNESS,  # using the NeoPixel brightness
                      RED[2] * BRIGHTNESS)) # setting.
SPARKLE = SparklePulse(PIXELS, period=2, speed=0.15,
                       max_intensity=BRIGHTNESS, color=BLUE)
ANIMATIONS = AnimationSequence(LARSON, SPARKLE, advance_interval=7,
                               auto_clear=False)

SERVO.angle = POSITION = NEXT_POSITION = 90
MOVING = False                # Initial state = paused
START_TIME = time.monotonic() # Initial time
DURATION = 1.0                # Hold initial position for 1 sec

while True: # Loop forever...

    # Move turret -- randomly looks around and pauses
    NOW = time.monotonic()
    ELAPSED = NOW - START_TIME # Seconds since start of motion or pause
    if ELAPSED >= DURATION:    # End motion/pause?
        MOVING = not MOVING    # Toggle between those two states
        START_TIME = NOW       # and record the new starting time
        ELAPSED = 0.0
        if MOVING:             # Switching from paused to moving
            POSITION = NEXT_POSITION
            while abs(POSITION - NEXT_POSITION) < 10:  # Min +/- 10 degrees
                NEXT_POSITION = random.uniform(0, 180) # Try, try again
            DURATION = 0.2 + 0.6 * abs(POSITION - NEXT_POSITION) / 180
        else:                  # Switching from moving to paused
            SERVO.angle = NEXT_POSITION         # Move to end of sweep
            DURATION = random.uniform(0.5, 2.5) # Pause time
    if MOVING:
        FRACTION = ELAPSED / DURATION                        # Linear 0 to 1
        FRACTION = (3 * FRACTION ** 2) - (2 * FRACTION ** 3) # Ease in/out
        SERVO.angle = POSITION + (NEXT_POSITION - POSITION) * FRACTION

    ANIMATIONS.animate() # Cycle through NeoPixel animations
