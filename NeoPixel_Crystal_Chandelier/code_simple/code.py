# SPDX-FileCopyrightText: 2021 Erin St Blaine for Adafruit Industries
#
# SPDX-License-Identifier: MIT

"""
Crystal Chandelier with Circuit Playground BlueFruit
Adafruit invests time and resources providing this open source code.
Please support Adafruit and open source hardware by purchasing
products from Adafruit!
Written by Erin St Blaine & Limor Fried for Adafruit Industries
Copyright (c) 2020-2021 Adafruit Industries
Licensed under the MIT license.
All text above must be included in any redistribution.
"""

# pylint: disable=import-error
# pylint: disable=no-member
import board
import digitalio
import rotaryio
import neopixel
from adafruit_circuitplayground import cp

from adafruit_led_animation.group import AnimationGroup
from adafruit_led_animation.animation.comet import Comet
from adafruit_led_animation.animation.solid import Solid
from adafruit_led_animation.color import (
    BLACK,
    PURPLE,
)

NEOPIXEL_PIN = board.A1 # NeoPixels connected here (crystals + rings)
NUM_PIXELS = 92        # Number of pixels in the crystals and rings

MIN_BRIGHTNESS = 1   # Minimum LED brightness as a percentage (0 to 100)
MAX_BRIGHTNESS = 25 # Maximum LED brighrness as a percentage (0 to 100)
MIN_FPS = 2         # Minimum animation speed in frames per second (>0)
MAX_FPS = 8        # Maximum animation speed in frames per second (>0)

# Set initial brightness and speed to center values
BRIGHTNESS = (MIN_BRIGHTNESS + MAX_BRIGHTNESS) // 2
FPS = (MIN_FPS + MAX_FPS) // 2
SPEED = 1 / FPS         # Integer frames-per-second to seconds interval
LEVEL = BRIGHTNESS * 0.01 # Integer brightness percentage to 0.0-1.0 coeff.

button = digitalio.DigitalInOut(board.A5)
button.direction = digitalio.Direction.INPUT
button.pull = digitalio.Pull.UP
BUTTON_STATE = None
BUTTON_VALUE = None

PIXELS = neopixel.NeoPixel(NEOPIXEL_PIN, NUM_PIXELS, brightness=LEVEL,
                           auto_write=False)

# NeoPixels off ASAP on startup
cp.pixels.fill(0) # Onboard pixels
cp.pixels.show()
PIXELS.fill(0) # NeoPixel strip
PIXELS.show()

ENCODER = rotaryio.IncrementalEncoder(board.A2, board.A3)

# LED ANIMATIONS -----------------------------------------------------------

COMET = Comet(PIXELS, speed=SPEED, tail_length=8,
              color=PURPLE, bounce=True)
CP_COMET = Comet(cp.pixels, speed=SPEED, tail_length=8,
                 color=PURPLE, bounce=True)
DARK_RINGS = Solid(PIXELS, color=BLACK)
DARK_CPB = Solid(cp.pixels, color=BLACK)
DARK = AnimationGroup(
        DARK_RINGS,
        DARK_CPB,
        )

# Animations Playlist, reorder as desired. AnimationGroups play at same time
ANIMATIONS = AnimationGroup(
        COMET,
        CP_COMET,
        )


# MAIN LOOP ----------------------------------------------------------------

LAST_POSITION = ENCODER.position
MODE = 1
while True:

    POSITION = ENCODER.position
    if POSITION != LAST_POSITION:
        MOVE = POSITION - LAST_POSITION
        if cp.switch:

            FPS = max(MIN_FPS, min(FPS + MOVE, MAX_FPS))
            SPEED = 1.0 / FPS
            COMET.speed = SPEED
            print("comet speed = ", SPEED)
        else:
            BRIGHTNESS = max(MIN_BRIGHTNESS, min(BRIGHTNESS + MOVE,
                                                 MAX_BRIGHTNESS))
            LEVEL = BRIGHTNESS * 0.1
            if LEVEL > 1:
                LEVEL = 1
            cp.pixels.brightness = LEVEL
            PIXELS.brightness = LEVEL
            print("brightness = ", LEVEL)
        LAST_POSITION = POSITION
    if not BUTTON_VALUE and BUTTON_STATE is None:
        BUTTON_STATE = "pressed"
    if BUTTON_VALUE and BUTTON_STATE == "pressed":
        print("Button pressed.")
        if MODE == 1:
            MODE = 2
        else:
            MODE = 1
        BUTTON_STATE = None
    if MODE == 1:
        ANIMATIONS.animate()
    else:
        DARK.animate()
