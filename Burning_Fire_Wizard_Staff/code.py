# SPDX-FileCopyrightText: 2019 Kattni Rembor Adafruit Industries
# SPDX-FileCopyrightText: 2019 Erin St Blaine for Adafruit Industries
# SPDX-FileCopyrightText: 2019 Limor Fried for Adafruit Industries
#
# SPDX-License-Identifier: MIT

"""
Prop-Maker based Burning Wizard Staff
Adafruit invests time and resources providing this open source code.
Please support Adafruit and open source hardware by purchasing
products from Adafruit!
Written by Kattni Rembor, Erin St Blaine & Limor Fried for Adafruit Industries
Copyright (c) 2020 Adafruit Industries
Licensed under the MIT license.
All text above must be included in any redistribution.
"""

import time
import random
import digitalio
import audioio
import audiocore
import board
import neopixel
import adafruit_lis3dh

# CHANGE TO MATCH YOUR RING AND STRIP SETUP
NUM_RING = 12   #12 pixel ring
NUM_STRIP = 44  # 44 pixels in my NeoPixel strip
NUM_PIXELS = NUM_STRIP + NUM_RING  #total number of pixels

NEOPIXEL_PIN = board.D5  # PropMaker Wing uses D5 for NeoPixel plug
POWER_PIN = board.D10


# CUSTOMISE COLORS HERE:
COLOR = (200, 30, 0)      # Default idle is orange
ALT_COLOR = (0, 200, 200)  # hit color is teal
SWING_COLOR = (200, 200, 200) #swing animation color is white
TOP_COLOR = (100, 100, 0)  #top color is yellow-green
YELL_COLOR = (200, 0, 200)  #yell color is purple

# CUSTOMISE IDLE PULSE SPEED HERE: 0 is fast, above 0 slows down
IDLE_PULSE_SPEED = 0  # Default is 0 seconds
SWING_BLAST_SPEED = 0.007

# CUSTOMISE BRIGHTNESS HERE: must be a number between 0 and 1
IDLE_PULSE_BRIGHTNESS_MIN = 0.2  # Default minimum idle pulse brightness
IDLE_PULSE_BRIGHTNESS_MAX = 1  # Default maximum idle pulse brightness

# CUSTOMISE SENSITIVITY HERE: smaller numbers = more sensitive to motion
HIT_THRESHOLD = 1150
SWING_THRESHOLD = 800
YELL_THRESHOLD = 700

# Set to the length in seconds of the "on.wav" and "yell1.wav" files
POWER_ON_SOUND_DURATION = 3.0
YELL_SOUND_DURATION = 1.0


enable = digitalio.DigitalInOut(POWER_PIN)
enable.direction = digitalio.Direction.OUTPUT
enable.value = False

# Set up NeoPixels
strip = neopixel.NeoPixel(NEOPIXEL_PIN, NUM_PIXELS, brightness=1, auto_write=False)
strip.fill(0)  # NeoPixels off ASAP on startup
strip.show()

audio = audioio.AudioOut(board.A0)  # Speaker
wave_file = None

# Set up accelerometer on I2C bus, 4G range:
i2c = board.I2C()  # uses board.SCL and board.SDA
# i2c = board.STEMMA_I2C()  # For using the built-in STEMMA QT connector on a microcontroller
accel = adafruit_lis3dh.LIS3DH_I2C(i2c)
accel.range = adafruit_lis3dh.RANGE_4_G

COLOR_IDLE = COLOR # 'idle' color is the default for the staff handle
COLOR_HIT = ALT_COLOR  # "hit" color is ALT_COLOR set above
COLOR_SWING = SWING_COLOR  # "swing" color is SWING_COLOR set above
COLOR_TOP = TOP_COLOR  #"top" color is idle color for the ring


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
        wave = audiocore.WaveFile(wave_file)
        audio.play(wave, loop=loop)
    except OSError:
        pass # we'll just skip playing then


def power(sound, duration, reverse):
    """
    Animate NeoPixels with accompanying sound effect for power on.
    @param sound: sound name (similar format to play_wav() above)
    @param duration: estimated duration of sound, in seconds (>0.0)
    @param reverse: Reverses animation. If True, begins animation at end of strip.
    """
    if reverse:
        prev = NUM_PIXELS
    else:
        prev = 0
    start_time = time.monotonic()  # Save audio start time
    play_wav(sound)
    while True:
        elapsed = time.monotonic() - start_time  # Time spent playing sound
        if elapsed > duration:                   # Past sound duration?
            break                                # Stop animating
        total_animation_time = elapsed / duration            # Animation time, 0.0 to 1.0
        if reverse:
            total_animation_time = 1.0 - total_animation_time            # 1.0 to 0.0 if reverse
        threshold = int(NUM_PIXELS * total_animation_time + 0.5)
        num = threshold - prev # Number of pixels to light on this pass
        if num != 0:
            if reverse:
                strip[threshold:prev] = [ALT_COLOR] * -num
            else:
                strip[prev:threshold] = [ALT_COLOR] * num
            strip.show()
            prev = threshold


def mix(color_1, color_2, weight_2):
    """
    Blend between two colors with a given ratio.
    :param color_1:  first color, as an (r,g,b) tuple
    :param color_2:  second color, as an (r,g,b) tuple
    :param weight_2: Blend weight (ratio) of second color, 0.0 to 1.0
    :return (r,g,b) tuple, blended color
    """
    if weight_2 < 0.0:
        weight_2 = 0.0
    elif weight_2 > 1.0:
        weight_2 = 1.0
    weight_1 = 1.0 - weight_2
    return (int(color_1[0] * weight_1 + color_2[0] * weight_2),
            int(color_1[1] * weight_1 + color_2[1] * weight_2),
            int(color_1[2] * weight_1 + color_2[2] * weight_2))

# List of swing wav files without the .wav in the name for use with play_wav()
swing_sounds = [
    'swing1',
    'swing2',
    'swing3',
]

# List of hit wav files without the .wav in the name for use with play_wav()
hit_sounds = [
    'hit1',
    'hit2',
    'hit3',
    'hit4',
]

# List of yell wav files without the .wav in the name for use with play_wav()
yell_sounds = [
    'yell1',
]


mode = 0  # Initial mode = OFF

# Setup idle pulse
idle_brightness = IDLE_PULSE_BRIGHTNESS_MIN  # current brightness of idle pulse
idle_increment = 0.01  # Initial idle pulse direction

# Main loop
while True:

    if mode == 0:  # If currently off...
        enable.value = True
        power('on', POWER_ON_SOUND_DURATION, True)  # Power up!
        play_wav('idle', loop=True)  # Play idle sound now
        mode = 1  # Idle mode
        time.sleep(1.0) #pause before moving on

        # Setup for idle pulse
        idle_brightness = IDLE_PULSE_BRIGHTNESS_MIN
        idle_increment = 0.01
        # lights the ring in COLOR_TOP color:
        strip[0:NUM_RING] = [([int(c*idle_brightness) for c in COLOR_TOP])] * NUM_RING
        # lights the strip in COLOR_IDLE color:
        strip[NUM_RING:NUM_PIXELS] = [([int(c*idle_brightness) for c in COLOR_IDLE])] * NUM_STRIP
        strip.show()

    elif mode >= 1:  # If not OFF mode...
        x, y, z = accel.acceleration  # Read accelerometer
        accel_total = x * x + z * z #x axis used for hit and for swing
        accel_yell = y * y + z * z  #y axis used for yell
        # Square root isn't needed, since we're
        # comparing thresholds...use squared values instead.)
        if accel_total > HIT_THRESHOLD:  # Large acceleration on x axis = HIT
            TRIGGER_TIME = time.monotonic()  # Save initial time of hit
            play_wav(random.choice(hit_sounds))  # Start playing 'hit' sound
            COLOR_ACTIVE = COLOR_HIT  # Set color to fade from
            mode = 3  # HIT mode
        elif mode == 1 and accel_total > SWING_THRESHOLD:  # Mild acceleration on x axis = SWING
            TRIGGER_TIME = time.monotonic()  # Save initial time of swing
            play_wav(random.choice(swing_sounds))  # Randomly choose from available swing sounds
            # make a larson scanner
            strip_backup = strip[0:-1]
            for p in range(-1, len(strip)):
                for i in range(p-1, p+2): # shoot a 'ray' of 3 pixels
                    if 0 <= i < len(strip):
                        strip[i] = COLOR_SWING
                strip.show()
                time.sleep(SWING_BLAST_SPEED)
                if 0 <= (p-1) < len(strip):
                    strip[p-1] = strip_backup[p-1]  # restore previous color at the tail
                strip.show()
            while audio.playing:
                pass # wait till we're done
            mode = 2  # we'll go back to idle mode
        elif mode == 1 and accel_yell > YELL_THRESHOLD:  # Motion on Y axis = YELL
            TRIGGER_TIME = time.monotonic()  # Save initial time of swing
            # run a color down the staff, opposite of power-up
            previous = 0
            audio_start_time = time.monotonic()  # Save audio start time
            play_wav(random.choice(yell_sounds))  # Randomly choose from available yell sounds
            sound_duration = YELL_SOUND_DURATION
            while True:
                time_elapsed = time.monotonic() - audio_start_time  # Time spent playing sound
                if time_elapsed > sound_duration:  # Past sound duration?
                    break  # Stop animating
                animation_time = time_elapsed / sound_duration  # Animation time, 0.0 to 1.0
                pixel_threshold = int(NUM_PIXELS * animation_time + 0.5)
                num_pixels = pixel_threshold - previous  # Number of pixels to light on this pass
                if num_pixels != 0:
                    # light pixels in YELL_COLOR:
                    strip[previous:pixel_threshold] = [YELL_COLOR] * num_pixels
                    strip.show()
                    previous = pixel_threshold
            while audio.playing:
                pass # wait till we're done
            mode = 4  # we'll go back to idle mode
        elif mode == 1:
            # Idle pulse
            idle_brightness += idle_increment  # Pulse up
            if idle_brightness > IDLE_PULSE_BRIGHTNESS_MAX or \
               idle_brightness < IDLE_PULSE_BRIGHTNESS_MIN:  # Then...
                idle_increment *= -1  # Pulse direction flip
            # light the ring:
            strip[0:NUM_RING] = [([int(c*idle_brightness) for c in COLOR_TOP])] * NUM_RING
            # light the strip:
            strip[NUM_RING:NUM_PIXELS] = [([int(c*idle_brightness) for c in
                                            COLOR_IDLE])] * NUM_STRIP
            strip.show()
            time.sleep(IDLE_PULSE_SPEED)  # Idle pulse speed set above
        elif mode > 1:  # If in SWING or HIT or YELL mode...
            if audio.playing:  # And sound currently playing...
                blend = time.monotonic() - TRIGGER_TIME  # Time since triggered
                if mode == 2:  # If SWING,
                    blend = abs(0.5 - blend) * 3.0  # ramp up, down
                strip.fill(mix(COLOR_ACTIVE, COLOR, blend))  # Fade from hit/swing to base color
                strip.show()
            else:  # No sound now, but still SWING or HIT modes
                play_wav('idle', loop=True)  # Resume idle sound
                mode = 1  # Return to idle mode
