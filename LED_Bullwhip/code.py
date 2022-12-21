# SPDX-FileCopyrightText: 2020 Erin St Blaine for Adafruit Industries
# SPDX-FileCopyrightText: 2020 Limor Fried for Adafruit Industries
#
# SPDX-License-Identifier: MIT
"""
Prop-Maker based LED Bullwhip
Adafruit invests time and resources providing this open source code.
Please support Adafruit and open source hardware by purchasing
products from Adafruit!
Written by Erin St Blaine & Limor Fried for Adafruit Industries
Copyright (c) 2019-2020 Adafruit Industries
Licensed under the MIT license.
All text above must be included in any redistribution.
"""

import time
import array
import math
import digitalio
import audiobusio
import board
import neopixel
import adafruit_lsm6ds

# CUSTOMISE COLORS HERE:
COLOR = (40, 3, 0)      # Default idle is blood orange
HIT_COLOR = (0, 250, 0)  # hit color is green
LIGHT_WAVE_COLOR = (200, 50, 200) # purple
DARK_COLOR = (0, 0, 0)
CRACK_COLOR = (250, 250, 250) #white


# CUSTOMISE IDLE PULSE SPEED HERE: 0 is fast, above 0 slows down
IDLE_PULSE_SPEED = 0  # Default is 0 seconds
SWING_BLAST_SPEED = 0.007

# CUSTOMISE BRIGHTNESS HERE: must be a number between 0 and 1
IDLE_PULSE_BRIGHTNESS_MIN = 0.1  # Default minimum idle pulse brightness
IDLE_PULSE_BRIGHTNESS_MAX = 0.5  # Default maximum idle pulse brightness

# CUSTOMISE SENSITIVITY HERE: smaller numbers = more sensitive to motion
HIT_THRESHOLD = 1150
SWING_THRESHOLD = 750
SOUND_THRESHOLD = 2000

# Set to the length in seconds for the animations
POWER_ON_DURATION = 1.7
LIGHT_WAVE_DURATION = 1
HIT_DURATION = 2
SWING_DURATION = 0
FADE_DURATION = 1
WHIP_CRACK_DURATION = 0.5

NUM_PIXELS = 60  # Number of pixels used in project
NEOPIXEL_PIN = board.D5
POWER_PIN = board.D10
ONSWITCH_PIN = board.A1

led = digitalio.DigitalInOut(ONSWITCH_PIN)
led.direction = digitalio.Direction.OUTPUT
led.value = True

enable = digitalio.DigitalInOut(POWER_PIN)
enable.direction = digitalio.Direction.OUTPUT
enable.value = False

strip = neopixel.NeoPixel(NEOPIXEL_PIN, NUM_PIXELS, brightness=1, auto_write=False)
strip.fill(0)  # NeoPixels off ASAP on startup
strip.show()

WAVE_FILE = None

i2c = board.I2C()  # uses board.SCL and board.SDA
# i2c = board.STEMMA_I2C()  # For using the built-in STEMMA QT connector on a microcontroller

#Set up accelerometer & mic

sensor = adafruit_lsm6ds.LSM6DS33(i2c)
mic = audiobusio.PDMIn(board.MICROPHONE_CLOCK,
                       board.MICROPHONE_DATA,
                       sample_rate=16000,
                       bit_depth=16)

COLOR_IDLE = COLOR # 'idle' color is the default
COLOR_HIT = HIT_COLOR  # "hit" color is HIT_COLOR set above
COLOR_SWING = LIGHT_WAVE_COLOR  # "swing" color is HIT_COLOR set above
COLOR_ACTIVE = LIGHT_WAVE_COLOR


def mean(values):
    ''' Remove DC bias before computing RMS.'''
    return sum(values) / len(values)

def normalized_rms(values):
    ''' Normalize values'''
    minbuf = int(mean(values))
    samples_sum = sum(
        float(sample - minbuf) * (sample - minbuf)
        for sample in values
    )

    return math.sqrt(samples_sum / len(values))


samples = array.array('H', [0] * 160)
mic.record(samples, len(samples))

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

def power_on(duration):
    """
    Animate NeoPixels for power on.
    :param duration: estimated duration of sound, in seconds (>0.0)
    """
    prev = 0
    start_time = time.monotonic()  # Save start time
    while True:
        elapsed = time.monotonic() - start_time  # Time spent
        if elapsed > duration:  # Past duration?
            break  # Stop animating
        animation_time = elapsed / duration  # Animation time, 0.0 to 1.0
        threshold = int(NUM_PIXELS * animation_time + 0.5)
        num = threshold - prev  # Number of pixels to light on this pass
        if num != 0:
            strip[prev:threshold] = [COLOR] * num
            strip.show()
            prev = threshold

def fade(duration):
    """
    Animate NeoPixels for hit/fade animation
    :param duration: estimated duration of sound, in seconds (>0.0)
    """
    prev = 0
    hit_time = time.monotonic()  # Save start time
    while True:
        elapsed = time.monotonic() - hit_time  # Time spent
        if elapsed > duration:  # Past duration?
            break  # Stop animating
        animation_time = elapsed / duration  # Animation time, 0.0 to 1.0
        threshold = int(NUM_PIXELS * animation_time + 0.5)
        num = threshold - prev  # Number of pixels to light on this pass
        if num != 0:
            blend = time.monotonic() - hit_time  # Time since triggered
            blend = abs(0.5 - blend) * 2.0  # ramp up, down
            strip.fill(mix(COLOR_ACTIVE, COLOR, blend))  # Fade from hit/swing to base color
            strip.show()

def light_wave(duration):
    """
    Animate NeoPixels for swing animatin
    :param duration: estimated duration of sound, in seconds (>0.0)
    """
    prev = 0
    swing_time = time.monotonic()  # Save start time
    while True:
        elapsed = time.monotonic() - swing_time  # Time spent
        if elapsed > duration:  # Past duration?
            break  # Stop animating
        animation_time = elapsed / duration  # Animation time, 0.0 to 1.0
        threshold = int(NUM_PIXELS * animation_time + 0.5)
        num = threshold - prev  # Number of pixels to light on this pass
        if num != 0:
            strip[prev:threshold] = [CRACK_COLOR] * num
            strip.show()
            prev = threshold

def whip_crack(duration):
    """
    Animate NeoPixels for swing animatin
    :param duration: estimated duration of sound, in seconds (>0.0)
    """
    prev = 0
    crack_time = time.monotonic()  # Save start time
    while True:
        elapsed = time.monotonic() - crack_time  # Time spent
        if elapsed > duration:  # Past duration?
            break  # Stop animating
        animation_time = elapsed / duration  # Animation time, 0.0 to 1.0
        threshold = int(NUM_PIXELS * animation_time + 0.5)
        num = threshold - prev  # Number of pixels to light on this pass
        if num != 0:
            strip.fill(CRACK_COLOR)
            strip.show()
            time.sleep(0.01)
            strip.fill(DARK_COLOR)
            strip.show()
            time.sleep(0.03)
            strip.fill(CRACK_COLOR)
            strip.show()
            time.sleep(0.02)
            strip.fill(DARK_COLOR)
            strip.show()
            time.sleep(0.005)
            strip.fill(CRACK_COLOR)
            strip.show()
            time.sleep(0.01)
            strip.fill(DARK_COLOR)
            strip.show()
            time.sleep(0.03)
            prev = threshold



MODE = 0  # Initial MODE = OFF

# Setup idle pulse
IDLE_BRIGHTNESS = IDLE_PULSE_BRIGHTNESS_MIN  # current brightness of idle pulse
IDLE_INCREMENT = 0.01  # Initial idle pulse direction

# Main loop
while True:
    if MODE == 0:  # If currently off...
        enable.value = True
        power_on(POWER_ON_DURATION)  # Power up!
        MODE = 1  # Idle MODE

        # Setup for idle pulse
        IDLE_BRIGHTNESS = IDLE_PULSE_BRIGHTNESS_MIN
        IDLE_INCREMENT = 0.01
        strip.fill([int(c*IDLE_BRIGHTNESS) for c in COLOR])
        strip.show()

    elif MODE >= 1:  # If not OFF MODE...
        samples = array.array('H', [0] * 160)
        mic.record(samples, len(samples))
        magnitude = normalized_rms(samples)
        print("Sound level:", normalized_rms(samples))
        if magnitude > SOUND_THRESHOLD:
            whip_crack(WHIP_CRACK_DURATION)
            MODE = 4
        x, y, z = sensor.acceleration
        accel_total = x * x + z * z
        # (Y axis isn't needed, due to the orientation that the Prop-Maker
        # Wing is mounted.  Also, square root isn't needed, since we're
        # comparing thresholds...use squared values instead.)
        if accel_total > HIT_THRESHOLD:  # Large acceleration = HIT
            TRIGGER_TIME = time.monotonic()  # Save initial time of hit
            #play_wav("/sounds/hit1.wav")  # Start playing 'hit' sound
            COLOR_ACTIVE = COLOR_HIT  # Set color to fade from
            MODE = 3  # HIT MODE
            print("playing HIT")
        elif MODE == 1 and accel_total > SWING_THRESHOLD:  # Mild = SWING
            # make a larson scanner animation_time
            strip.fill(DARK_COLOR)
            strip_backup = strip[0:-1]
            for p in range(-1, len(strip)):
                for i in range(p-1, p+10): # shoot a 'ray' of 3 pixels
                    if 0 <= i < len(strip):
                        strip[i] = COLOR_SWING
                strip.show()
                time.sleep(SWING_BLAST_SPEED)
                if 0 <= (p-1) < len(strip):
                    strip[p-1] = strip_backup[p-1]  # restore previous color at the tail
                strip.show()
            MODE = 2  # we'll go back to idle MODE
            print("playing SWING")
        elif MODE == 1:
            # Idle pulse
            IDLE_BRIGHTNESS += IDLE_INCREMENT  # Pulse up
            if IDLE_BRIGHTNESS > IDLE_PULSE_BRIGHTNESS_MAX or \
               IDLE_BRIGHTNESS < IDLE_PULSE_BRIGHTNESS_MIN:  # Then...
                IDLE_INCREMENT *= -1  # Pulse direction flip
            strip.fill([int(c*IDLE_BRIGHTNESS) for c in COLOR_IDLE])
            strip.show()
            time.sleep(IDLE_PULSE_SPEED)  # Idle pulse speed set above
        elif MODE > 1:  # If in SWING or HIT MODE...
            if MODE == 3:
                fade(FADE_DURATION)
#             elif MODE == 2:  # If SWING,
#                 power_on(POWER_ON_DURATION)
            MODE = 1  # Return to idle mode
