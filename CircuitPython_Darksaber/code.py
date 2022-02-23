# SPDX-FileCopyrightText: Kattni Rembor for Adafruit Industries
# SPDX-FileCopyrightText: Limor Fried for Adafruit Industries
# SPDX-FileCopyrightText: 2019 Liz Clark for Adafruit Industries
#
# SPDX-License-Identifier: MIT

"""
Prop-Maker based Darksaber
Adapted from the Prop-Maker based Master Sword code
by Kattni Rembor & Limor Fried
Adafruit invests time and resources providing this open source code.
Please support Adafruit and open source hardware by purchasing
products from Adafruit!
Written by Liz Clark for Adafruit Industries
Copyright (c) 2021 Adafruit Industries
Licensed under the MIT license.
All text above must be included in any redistribution.
"""

import time
import random
import board
from digitalio import DigitalInOut, Direction
import neopixel
import adafruit_lis3dh
from adafruit_led_animation.animation.solid import Solid
from adafruit_led_animation.animation.pulse import Pulse
from adafruit_led_animation.animation.comet import Comet

# CUSTOMISE SENSITIVITY HERE: smaller numbers = more sensitive to motion
HIT_THRESHOLD = 250
SWING_THRESHOLD = 150

# Set to the length in seconds of the "on.wav" file
POWER_ON_SOUND_DURATION = 1.7

#  NeoPixel setup
NUM_PIXELS = 34  # Number of pixels used in project
NEOPIXEL_PIN = board.D5
POWER_PIN = board.D10

enable = DigitalInOut(POWER_PIN)
enable.direction = Direction.OUTPUT
enable.value = False

strip = neopixel.NeoPixel(NEOPIXEL_PIN, NUM_PIXELS, brightness=.5, auto_write=False)
strip.fill(0)  # NeoPixels off ASAP on startup
strip.show()

#  default NeoPixel color is white
COLOR = (255, 255, 255)

#  NeoPixel animations
pulse = Pulse(strip, speed=0.05, color=COLOR, period=3)
solid = Solid(strip, color=COLOR)
comet = Comet(strip, speed=0.05, color=COLOR, tail_length=40)

#audio
try:
    from audiocore import WaveFile
except ImportError:
    from audioio import WaveFile

try:
    from audioio import AudioOut
except ImportError:
    try:
        from audiopwmio import PWMAudioOut as AudioOut
    except ImportError:
        pass  # not always supported by every board!

audio = AudioOut(board.A0)  # Speaker
wave_file = None

# Set up accelerometer on I2C bus, 4G range:
i2c = board.I2C()
accel = adafruit_lis3dh.LIS3DH_I2C(i2c)
accel.range = adafruit_lis3dh.RANGE_4_G

def play_wav(name, loop=False):
    """
    Play a WAV file in the 'sounds' directory.
    :param name: partial file name string, complete name will be built around
                 this, e.g. passing 'foo' will play file 'sounds/foo.wav'.
    :param loop: if True, sound will repeat indefinitely (until interrupted
                 by another sound).
    """
    global wave_file  # pylint: disable=global-statement
    print("playing", name)
    if wave_file:
        wave_file.close()
    try:
        wave_file = open('sounds/' + name + '.wav', 'rb')
        wave = WaveFile(wave_file)
        audio.play(wave, loop=loop)
    except OSError:
        pass # we'll just skip playing then


def power_on(sound, duration):
    """
    Animate NeoPixels with accompanying sound effect for power on.
    :param sound: sound name (similar format to play_wav() above)
    :param duration: estimated duration of sound, in seconds (>0.0)
    """
    start_time = time.monotonic()  # Save audio start time
    play_wav(sound)
    while True:
        elapsed = time.monotonic() - start_time  # Time spent playing sound
        if elapsed > duration:  # Past sound duration?
            break  # Stop animating
        comet.animate()

# List of swing wav files without the .wav in the name for use with play_wav()
swing_sounds = [
    'swing1',
    'swing2',
    'swing3',
    'swing4',
]

# List of hit wav files without the .wav in the name for use with play_wav()
hit_sounds = [
    'hit1',
    'hit2',
    'hit3',
    'hit4',
]

mode = 0  # Initial mode = OFF

#RGB LED
red_led = DigitalInOut(board.D11)
green_led = DigitalInOut(board.D12)
blue_led = DigitalInOut(board.D13)

red_led.direction = Direction.OUTPUT
green_led.direction = Direction.OUTPUT
blue_led.direction = Direction.OUTPUT

blue_led.value = True
red_led.value = True
green_led.value = True

# Main loop
while True:

    if mode == 0:  # If currently off...
        enable.value = True
        power_on('on', POWER_ON_SOUND_DURATION)  # Power up!
        play_wav('idle', loop=True)  # Play idle sound now
        mode = 1  # Idle mode

    elif mode >= 1:  # If not OFF mode...
        x, y, z = accel.acceleration  # Read accelerometer
        accel_total = x * x + z * z
        # (Y axis isn't needed, due to the orientation that the Prop-Maker
        # Wing is mounted.  Also, square root isn't needed, since we're
        # comparing thresholds...use squared values instead.)
        if accel_total > HIT_THRESHOLD:  # Large acceleration = HIT
            TRIGGER_TIME = time.monotonic()  # Save initial time of hit
            play_wav(random.choice(hit_sounds))  # Start playing 'hit' sound
            solid.animate()
            mode = 3  # HIT mode
        elif mode == 1 and accel_total > SWING_THRESHOLD:  # Mild = SWING
            TRIGGER_TIME = time.monotonic()  # Save initial time of swing
            play_wav(random.choice(swing_sounds))  # Randomly choose from available swing sounds
            while audio.playing:
                pass # wait till we're done
            mode = 2  # we'll go back to idle mode

        elif mode == 1:
            pulse.animate()
        elif mode > 1:  # If in SWING or HIT mode...
            if audio.playing:  # And sound currently playing...
                blend = time.monotonic() - TRIGGER_TIME  # Time since triggered
                if mode == 2:  # If SWING,
                    blend = abs(0.5 - blend) * 2.0  # ramp up, down
            else:  # No sound now, but still SWING or HIT modes
                play_wav('idle', loop=True)  # Resume idle sound
                mode = 1  # Return to idle mode
