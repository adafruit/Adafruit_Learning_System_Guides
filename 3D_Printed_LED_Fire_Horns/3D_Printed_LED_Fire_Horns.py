# Fiery demon horns (rawr!) for Adafruit Trinket/Gemma.
# Adafruit invests time and resources providing this open source code,
# please support Adafruit and open-source hardware by purchasing
# products from Adafruit!

import board
import neopixel
from analogio import AnalogIn
# pylint: disable=global-statement

try:
    import urandom as random
except ImportError:
    import random

# /\  ->   Fire-like effect is the sum_total of multiple triangle
# ____/  \____  waves in motion, with a 'warm' color map applied.
n_horns = 1             # number of horns
led_pin = board.D0      # which pin your pixels are connected to
n_leds = 30             # number of LEDs per horn
frames_per_second = 50  # animation frames per second
brightness = 0          # current wave height
fade = 0                # Decreases brightness as wave moves
pixels = neopixel.NeoPixel(led_pin, n_leds, brightness=1, auto_write=False)
offset = 0

# Coordinate space for waves is 16x the pixel spacing,
# allowing fixed-point math to be used instead of floats.
lower = 0       # lower bound of wave
upper = 1       # upper bound of wave
mid = 2         # midpoint (peak) ((lower+upper)/2)
vlower = 3      # velocity of lower bound
vupper = 4      # velocity of upper bound
intensity = 5   # brightness at peak

y = 0
brightness = 0
count = 0

# initialize 3D list
wave = [[0] * 6] * 6, [[0] * 6] * 6, [[0] * 6] * 6, [[0] * 6] * 6, [[0] * 6] * 6, [[0] * 6] * 6

# Number of simultaneous waves (per horn)
n_waves = len(wave)

# Gamma-correction table
gamma = [
    0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
    0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 1,
    1, 1, 1, 1, 1, 1, 1, 1, 1, 2, 2, 2, 2, 2, 2, 2,
    2, 3, 3, 3, 3, 3, 3, 3, 4, 4, 4, 4, 4, 5, 5, 5,
    5, 6, 6, 6, 6, 7, 7, 7, 7, 8, 8, 8, 9, 9, 9, 10,
    10, 10, 11, 11, 11, 12, 12, 13, 13, 13, 14, 14, 15, 15, 16, 16,
    17, 17, 18, 18, 19, 19, 20, 20, 21, 21, 22, 22, 23, 24, 24, 25,
    25, 26, 27, 27, 28, 29, 29, 30, 31, 32, 32, 33, 34, 35, 35, 36,
    37, 38, 39, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50, 50,
    51, 52, 54, 55, 56, 57, 58, 59, 60, 61, 62, 63, 64, 66, 67, 68,
    69, 70, 72, 73, 74, 75, 77, 78, 79, 81, 82, 83, 85, 86, 87, 89,
    90, 92, 93, 95, 96, 98, 99, 101, 102, 104, 105, 107, 109, 110,
    112, 114, 115, 117, 119, 120, 122, 124, 126, 127, 129, 131, 133,
    135, 137, 138, 140, 142, 144, 146, 148, 150, 152, 154, 156, 158,
    160, 162, 164, 167, 169, 171, 173, 175, 177, 180, 182, 184, 186,
    189, 191, 193, 196, 198, 200, 203, 205, 208, 210, 213, 215, 218,
    220, 223, 225, 228, 231, 233, 236, 239, 241, 244, 247, 249, 252,
    255
]


def random_wave(he, wi):
    wave[he][wi][upper] = -1                                  # Always start below head of strip
    wave[he][wi][lower] = -16 * (3 + random.randint(0,4))     # Lower end starts ~3-7 pixels back
    wave[he][wi][mid] = (wave[he][wi][lower]+ wave[he][wi][upper]) / 2
    wave[he][wi][vlower] = 3 + random.randint(0,4)            #  Lower end moves at ~1/8 to 1/pixels
    wave[he][wi][vupper] = wave[he][wi][vlower]+ random.randint(0,4) # Upper end moves a bit faster
    wave[he][wi][intensity] = 300 + random.randint(0,600)

def setup():
    global fade

    # Random number generator is seeded from an unused 'floating'
    # analog input - this helps ensure the random color choices
    # aren't always the same order.
    pin = AnalogIn(board.A0)
    random.seed(pin.value)
    pin.deinit()

    for he in range(n_horns):
        for wi in range(n_waves):
            random_wave(he, wi)

    fade = 233 + n_leds / 2

    if fade > 233:
        fade = 233

setup()

while True:

    h = w = i = r = g = b = 0
    x = 0

    for h in range(n_horns):                # For each horn...
        x = 7
        sum_total = 0
        for i in range(n_leds):             # For each LED along horn...
            x += 16
            for w in range(n_waves):        # For each wave of horn...
                if (x < wave[h][w][lower]) or (x > wave[h][w][upper]):
                    continue                # Out of range
                if x <= wave[h][w][mid]:    # Lower half of wave (ramping up peak brightness)
                    sum_top = wave[h][w][intensity] * (x - wave[h][w][lower])
                    sum_bottom = (wave[h][w][mid] - wave[h][w][lower])
                    sum_total += sum_top /  sum_bottom
                else:                       # Upper half of wave (ramping down from peak)
                    sum_top = wave[h][w][intensity] * (wave[h][w][upper] - x)
                    sum_bottom = (wave[h][w][upper] - wave[h][w][mid])
                    sum_total += sum_top / sum_bottom

            sum_total = int(sum_total)          # convert from decimal to whole number

            # Now the magnitude (sum_total) is remapped to color for the LEDs.
            # A blackbody palette is used - fades white-yellow-red-black.
            if sum_total < 255:                 # 0-254 = black to red-1
                r = gamma[sum_total]
                g = b = 0
            elif sum_total < 510:               # 255-509 = red to yellow-1
                r = 255
                g = gamma[sum_total - 255]
                b = 0
            elif sum_total < 765:               # 510-764 = yellow to white-1
                r = g = 255
                b = gamma[sum_total - 510]
            else:                               # 765+ = white
                r = g = b = 255
            pixels[i] = (r, g, b)

    for w in range(n_waves):                    # Update wave positions for each horn
        wave[h][w][lower] += wave[h][w][vlower] # Advance lower position
        if wave[h][w][lower] >= (n_leds * 16):  # Off end of strip?
            random_wave(h, w)                   # Yes, 'reboot' wave
        else:                                   # No, adjust other values...
            wave[h][w][upper] += wave[h][w][vupper]
            wave[h][w][mid] = (wave[h][w][lower] + wave[h][w][upper]) / 2
            wave[h][w][intensity] = (wave[h][w][intensity] * fade) / 256 # Dimmer

    pixels.show()
