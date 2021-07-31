"""
LED Ukulele with Feather Sense and PropMaker Wing
Adafruit invests time and resources providing this open source code.
Please support Adafruit and open source hardware by purchasing
products from Adafruit!
Written by Erin St Blaine & Limor Fried for Adafruit Industries
Copyright (c) 2019-2020 Adafruit Industries
Licensed under the MIT license.
All text above must be included in any redistribution.

MODES:
0 = off/powerup, 1 = sound reactive, 2 = non-sound reactive, 3 = tilt
Pluck high A on the E string to toggle sound reactive mode on or off
Pluck high A♭ on the E string to cycle through the animation modes
"""

import time
import array
import digitalio
import audiobusio
import board
import neopixel
from ulab.scipy.signal import spectrogram
from ulab import numpy as np
import adafruit_lsm6ds
from adafruit_led_animation.helper import PixelMap
from adafruit_led_animation.sequence import AnimationSequence
from adafruit_led_animation.group import AnimationGroup
from adafruit_led_animation.animation.sparkle import Sparkle
from adafruit_led_animation.animation.rainbow import Rainbow
from adafruit_led_animation.animation.rainbowchase import RainbowChase
from adafruit_led_animation.animation.rainbowcomet import RainbowComet
from adafruit_led_animation.animation.chase import Chase
from adafruit_led_animation.animation.comet import Comet
from adafruit_led_animation.color import colorwheel
from adafruit_led_animation.color import (
    BLACK,
    RED,
    ORANGE,
    BLUE,
    PURPLE,
    WHITE,
)

MAX_BRIGHTNESS = 0.3 #set max brightness for sound reactive mode
NORMAL_BRIGHTNESS = 0.1 #set brightness for non-reactive mode
VOLUME_CALIBRATOR = 50 #multiplier for brightness mapping
ROCKSTAR_TILT_THRESHOLD = 200 #shake threshold
SOUND_THRESHOLD = 430000 #main strum or pluck threshold

# Set to the length in seconds for the animations
POWER_ON_DURATION = 1.3
ROCKSTAR_TILT_DURATION = 1

NUM_PIXELS = 104  # Number of pixels used in project
NEOPIXEL_PIN = board.D5
POWER_PIN = board.D10

enable = digitalio.DigitalInOut(POWER_PIN)
enable.direction = digitalio.Direction.OUTPUT
enable.value = False

i2c = board.I2C()

pixels = neopixel.NeoPixel(NEOPIXEL_PIN, NUM_PIXELS, brightness=1, auto_write=False)
pixels.fill(0)  # NeoPixels off ASAP on startup
pixels.show()


#PIXEL MAPS: Used for reordering pixels so the animations can run in different configurations.
#My LED strips inside the neck are accidentally swapped left-right,
#so these maps also correct for that


#Bottom up along both sides at once
pixel_map_reverse = PixelMap(pixels, [
    0, 103, 1, 102, 2, 101, 3, 100, 4, 99, 5, 98, 6, 97, 7, 96, 8, 95, 9, 94, 10,
    93, 11, 92, 12, 91, 13, 90, 14, 89, 15, 88, 16, 87, 17, 86, 18, 85, 19, 84, 20,
    83, 21, 82, 22, 81, 23, 80, 24, 79, 25, 78, 26, 77, 27, 76, 28, 75, 29, 74, 30,
    73, 31, 72, 32, 71, 33, 70, 34, 69, 35, 68, 36, 67, 37, 66, 38, 65, 39, 64, 40,
    63, 41, 62, 42, 61, 43, 60, 44, 59, 45, 58, 46, 57, 47, 56, 48, 55, 49, 54, 50,
    53, 51, 52,
    ], individual_pixels=True)

#Starts at the bottom and goes around clockwise
pixel_map_around = PixelMap(pixels, [
    0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20,
    21, 22, 23, 24, 25, 26, 27, 75, 74, 73, 72, 71, 70, 69, 68, 67, 66, 65, 64,
    63, 62, 61, 60, 59, 58, 57, 56, 55, 54, 53, 52, 51, 50, 49, 48, 47, 46, 45,
    44, 43, 42, 41, 40, 39, 38, 37, 36, 35, 34, 33, 32, 31, 30, 29, 28,
    76, 77, 78, 79, 80, 81, 82, 83, 84, 85, 86, 87, 88, 89, 90, 91, 92, 93, 94,
    95, 96, 97, 98, 99, 100, 101, 102, 103,
    ], individual_pixels=True)

#Radiates from the center outwards like a starburst
pixel_map_radiate = PixelMap(pixels, [
    75, 73, 76, 27, 28, 74, 77, 26, 29, 73, 78, 25, 30, 72, 79, 24, 31, 71, 80,
    23, 32, 70, 81, 22, 33, 69, 82, 21, 34, 68, 83, 20, 35, 67, 84, 19, 36, 66,
    85, 18, 37, 65, 38, 86, 17, 64, 39, 87, 16, 63, 40, 88, 15, 62, 41, 89, 14,
    61, 42, 90, 13, 60, 43, 91, 12, 59, 44, 92, 11, 58, 45, 93, 10, 57, 46, 94,
    9, 56, 47, 95, 8, 55, 48, 96, 7, 54, 49, 97, 6, 53, 50, 98, 5, 52, 51, 99,
    4, 100, 3, 101, 2, 102, 1, 103, 0,
    ], individual_pixels=True)

#Top down along both sides at once
pixel_map_sweep = PixelMap(pixels, [
    51, 52, 50, 53, 49, 54, 48, 55, 47, 56, 46, 57, 45, 58, 44, 59, 43, 60, 42, 61,
    41, 62, 40, 63, 39, 64, 38, 65, 37, 66, 36, 67, 35, 68, 34, 69, 33, 70, 32, 71,
    31, 72, 30, 73, 29, 74, 28, 75, 27, 76, 27, 77, 26, 78, 25, 79, 24, 80, 23, 81,
    22, 82, 21, 83, 20, 84, 19, 85, 18, 86, 17, 87, 16, 88, 15, 89, 14, 90, 13, 91,
    12, 92, 11, 93, 10, 94, 9, 95, 8, 96, 7, 97, 6, 98, 5, 99, 4, 100, 3, 101, 2, 102, 1, 103, 0
    ], individual_pixels=True)

#Every other pixel, starting at the bottom and going upwards along both sides
pixel_map_skip = PixelMap(pixels, [
    0, 103, 2, 101, 4, 99, 6, 97, 8, 95, 10, 93, 12, 91, 14, 89, 16, 87, 18, 85, 20,
    83, 22, 81, 24, 79, 26, 77, 29, 74, 31, 72, 33, 70, 35, 68, 37, 66, 39, 64, 41,
    62, 43, 60, 45, 58, 47, 56, 49, 54, 51, 52,
    ], individual_pixels=True)

pixel_map = [
    pixel_map_reverse,
    pixel_map_around,
    pixel_map_radiate,
    pixel_map_sweep,
    pixel_map_skip,
]

#Set up accelerometer & mic
sensor = adafruit_lsm6ds.LSM6DS33(i2c)
mic = audiobusio.PDMIn(board.MICROPHONE_CLOCK,
                       board.MICROPHONE_DATA,
                       sample_rate=16000,
                       bit_depth=16)

NUM_SAMPLES = 256
samples_bit = array.array('H', [0] * (NUM_SAMPLES+3))

def power_on(duration):
    """
    Animate NeoPixels for power on.
    """
    start_time = time.monotonic()  # Save start time
    while True:
        elapsed = time.monotonic() - start_time  # Time spent
        if elapsed > duration:  # Past duration?
            break  # Stop animating
        powerup.animate()

def rockstar_tilt(duration):
    """
    Tilt animation - lightning effect with a rotating color
    :param duration: duration of the animation, in seconds (>0.0)
    """
    tilt_time = time.monotonic()  # Save start time
    while True:
        elapsed = time.monotonic() - tilt_time  # Time spent
        if elapsed > duration:  # Past duration?
            break  # Stop animating
        pixels.brightness = MAX_BRIGHTNESS
        pixels.fill(TILT_COLOR)
        pixels.show()
        time.sleep(0.01)
        pixels.fill(BLACK)
        pixels.show()
        time.sleep(0.03)
        pixels.fill(WHITE)
        pixels.show()
        time.sleep(0.02)
        pixels.fill(BLACK)
        pixels.show()
        time.sleep(0.005)
        pixels.fill(TILT_COLOR)
        pixels.show()
        time.sleep(0.01)
        pixels.fill(BLACK)
        pixels.show()
        time.sleep(0.03)

# Cusomize LED Animations  ------------------------------------------------------
powerup = RainbowComet(pixel_map[3], speed=0, tail_length=25, bounce=False)
rainbow = Rainbow(pixel_map[4], speed=0, period=6, name="rainbow", step=2.4)
rainbow_chase = RainbowChase(pixel_map[3], speed=0, size=3, spacing=15, step=10)
rainbow_chase2 = RainbowChase(pixel_map[2], speed=0, size=10, spacing=1, step=18)
chase = Chase(pixel_map[1], speed=0.1, color=RED, size=1, spacing=6)
rainbow_comet = RainbowComet(pixel_map[2], speed=0, tail_length=80, bounce=True)
rainbow_comet2 = RainbowComet(
    pixel_map[0], speed=0, tail_length=104, colorwheel_offset=80, bounce=True
    )
rainbow_comet3 = RainbowComet(
    pixel_map[1], speed=0, tail_length=25, colorwheel_offset=80, step=4, bounce=False
    )
strum = RainbowComet(
    pixel_map[3], speed=0, tail_length=25, bounce=False, colorwheel_offset=50, step=4
    )
lava = Comet(pixel_map[3], speed=0.01, color=ORANGE, tail_length=40, bounce=False)
sparkle = Sparkle(pixel_map[4], speed=0.01, color=BLUE, num_sparkles=10)
sparkle2 = Sparkle(pixel_map[1], speed=0.05, color=PURPLE, num_sparkles=4)

# Animations Playlist - reorder as desired. AnimationGroups play at the same time
animations = AnimationSequence(
    rainbow,
    rainbow_chase,
    rainbow_chase2,
    chase,
    lava,
    rainbow_comet,
    rainbow_comet2,
    AnimationGroup(
        sparkle,
        strum,
        ),
    AnimationGroup(
        sparkle2,
        rainbow_comet3,
        ),
    auto_clear=True,
    auto_reset=True,
)


MODE = 0
LASTMODE = 1 # start up in sound reactive mode
i = 0

# Main loop
while True:
    i = (i + 0.5) % 256  # run from 0 to 255
    TILT_COLOR = colorwheel(i)
    if MODE == 0:  # If currently off...
        enable.value = True
        power_on(POWER_ON_DURATION)  # Power up!
        MODE = LASTMODE

    elif MODE >= 1:  # If not OFF MODE...
        mic.record(samples_bit, len(samples_bit))
        samples = np.array(samples_bit[3:])
        spectrum = spectrogram(samples)
        spectrum = spectrum[:128]
        spectrum[0] = 0
        spectrum[1] = 0
        peak_idx = np.argmax(spectrum)
        peak_freq = peak_idx * 16000 / 256
#        print((peak_idx, peak_freq, spectrum[peak_idx]))
        magnitude = spectrum[peak_idx]
#         time.sleep(1)
        if peak_freq == 812.50 and magnitude > SOUND_THRESHOLD:
            animations.next()
            time.sleep(1)
        if peak_freq == 875 and magnitude > SOUND_THRESHOLD:
            if MODE == 1:
                MODE = 2
                print("mode = 2")
                LASTMODE = 2
                time.sleep(1)
            elif MODE == 2:
                MODE = 1
                print("mode = 1")
                LASTMODE = 1
                time.sleep(1)
    # Read accelerometer
        x, y, z = sensor.acceleration
        accel_total = x * x + y * y # x=tilt, y=rotate
#         print (accel_total)
        if accel_total > ROCKSTAR_TILT_THRESHOLD:
            MODE = 3
            print("Tilted: ", accel_total)
        if MODE == 1:
            VOLUME = magnitude / (VOLUME_CALIBRATOR * 100000)
            if VOLUME > MAX_BRIGHTNESS:
                VOLUME = MAX_BRIGHTNESS
#             print(VOLUME)
            pixels.brightness = VOLUME
#             time.sleep(2)
            animations.animate()
        elif MODE == 2:
            pixels.brightness = NORMAL_BRIGHTNESS
            animations.animate()
        elif MODE == 3:
            rockstar_tilt(ROCKSTAR_TILT_DURATION)
            MODE = LASTMODE
