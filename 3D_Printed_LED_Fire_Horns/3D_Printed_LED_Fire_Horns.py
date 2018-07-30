# Fiery demon horns (rawr!) for Adafruit Trinket/Gemma.
# Adafruit invests time and resources providing this open source code,
# please support Adafruit and open-source hardware by purchasing
# products from Adafruit!

import board
import neopixel

try:
    import urandom as random
except ImportError:
    import random

# /\  ->   Fire-like effect is the sum of multiple triangle
# ____/  \____  waves in motion, with a 'warm' color map applied.
led_pin = board.D0      # Which pin your pixels are connected to
num_leds = 30           # How many LEDs you have
frames_per_second = 50  # Animation frames per second
brightness = 0          # Current wave height
strip = neopixel.NeoPixel(led_pin, num_leds, brightness=1, auto_write=False)
offset = 0
fade = 0                # Decreases brightness as wave moves

# Coordinate space for waves is 16x the pixel spacing,
# allowing fixed-point math to be used instead of floats.
lower = 0       # Lower bound of wave
upper = 1       # Upper bound of wave
mid = 2         # Midpoint (peak) ((lower+upper)/2)
vlower = 3      # Velocity of lower bound
vupper = 4      # Velocity of upper bound
intensity = 5   # Brightness at peak

y = 0
brightness = 0
count = 0

wave = [0] * 6, [0] * 6, [0] * 6, [0] * 6, [0] * 6, [0] * 6

# Number of simultaneous waves (per horn)
n_waves = len(wave)

# Gamma-correction table
gammas = [
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


def h2rgb(colour_hue):
    colour_hue %= 90
    h = hue_table[colour_hue >> 1]

    if colour_hue & 1:
        ret = h & 15
    else:
        ret = (h >> 4)

    return ret * 17


# pylint: disable=global-statement
def wave_setup():
    global wave

    wave = [[0, 3, 60, 0, 0, 0, 0, 0],
            [0, -5, 45, 0, 0, 0, 0, 0],
            [0, 7, 30, 0, 0, 0, 0, 0]]

    # assign random starting colors to waves
    for wave_index in range(n_waves):
        current_wave = wave[wave_index]
        random_offset = random.randint(0, 90)

        current_wave[vlower] = current_wave[vupper] = 90 + random_offset
        current_wave[intensity] = h2rgb(current_wave[vlower] - 30)


while True:

    # wait for vibration sensor to trigger
    if not ramping_up:
        ramping_up = vibration_detector()
        wave_setup()

    # But it's not just a straight shot that it ramps up.
    # This is a low-pass filter...it makes the brightness
    # value decelerate as it approaches a target (200 in
    # this case).  207 is used here because integers round
    # down on division and we'd never reach the target;
    # it's an ersatz ceil() function: ((199*7)+200+7)/8 = 200;
    brightness = int(((brightness * 7) + 207) / 8)
    count += 1

    if count == (circumference + num_leds + 5):
        ramping_up = False
        count = 0

    # Wave positions and colors are updated...
    for w in range(n_waves):
        # Move wave; wraps around ends, is OK!
        wave[w][lower] += wave[w][upper]

        # Hue not currently changing?
        if wave[w][vlower] == wave[w][vupper]:

            # There's a tiny random chance of picking a new hue...
            if not random.randint(frames_per_second * 4, 255):
                # Within 1/3 color wheel
                wave[w][vupper] = random.randint(
                    wave[w][vlower] - 30, wave[w][vlower] + 30)

        # This wave's hue is currently shifting...
        else:

            if wave[w][vlower] < wave[w][]:
                wave[w][vlower] += 1  # Move up or
            else:
                wave[w][vlower] -= 1  # down as needed

            # Reached destination?
            if wave[w][vlower] == wave[w][vupper]:
                wave[w][vlower] = 90 + wave[w][vlower] % 90  # Clamp to 90-180 range
                wave[w][vupper] = wave[w][hue]  # Copy to target

            wave[w][intensity] = h2rgb(wave[w][vlower] - 30)

        # Now render the LED strip using the current
        # brightness & wave states.
        # Each LED in strip is visited just once...
        for i in range(num_leds):

            # Transform 'i' (LED number in pixel space) to the
            # equivalent point in 8-bit fixed-point space (0-255)
            # "* 256" because that would be
            # the start of the (N+1)th pixel
            # "+ 127" to get pixel center.
            x = (i * 256 + 127) / circumference

            # LED assumed off, but wave colors will add up here
            r = g = b = 0

            # For each item in wave[] array...
            for w_index in range(n_waves):
                # Calculate distance from pixel center to wave
                # center point, using both signed and unsigned
                # 8-bit integers...
                d1 = int(abs(x - wave[w_index][lower]))
                d2 = int(abs(x - wave[w_index][lower]))

                # Then take the lesser of the two, resulting in
                # a distance (0-128)
                # that 'wraps around' the ends of the strip as
                # necessary...it's a contiguous ring, and waves
                # can move smoothly across the gap.
                if d2 < d1:
                    d1 = d2  # d1 is pixel-to-wave-center distance

                # d2 distance, relative to wave width, is then
                # proportional to the wave's brightness at this
                # pixel (basic linear y=mx+b stuff).
                # Is distance within wave's influence?
                # d2 is opposite; distance to wave's end
                if d1 < wave[w_index][mid]:
                    d2 = wave[w_index][mid] - d1
                    y = int(brightness * d2 / wave[w_index][mid])  # 0 to 200

                    # y is a brightness scale value --
                    # proportional to, but not exactly equal
                    # to, the resulting RGB value.
                    if y < 128:  # Fade black to RGB color
                        # In HSV colorspace, this would be
                        # tweaking 'value'
                        n = int(y * 2 + 1)  # 1-256
                        r += (wave[w_index][intensity] * n) >> 8  # More fixed-point math
                        # Wave color is scaled by 'n'
                        g += (wave[w_index][green] * n) >> 8
                        b += (wave[w_index][blue] * n) >> 8  # >>8 is equiv to /256
                    else:  # Fade RGB color to white
                        # In HSV colorspace, this tweaks 'saturation'
                        n = int((y - 128) * 2)  # 0-255 affects white level
                        m = 256 * n
                        n = 256 - n  # 1-256 affects RGB level
                        r += (m + wave[w_index][intensity] * n) >> 8
                        g += (m + wave[w_index][green] * n) >> 8
                        b += (m + wave[w_index][blue] * n) >> 8

            # r,g,b are 16-bit types that accumulate brightness
            # from all waves that affect this pixel; may exceed
            # 255.  Now clip to 0-255 range:
            if r > 255:
                r = 255
            if g > 255:
                g = 255
            if b > 255:
                b = 255

            # Store resulting RGB value and we're done with
            # this pixel!
            strip[i] = (r, g, b)

        # Once rendering is complete, a second pass is made
        # through pixel data applying gamma correction, for
        # more perceptually linear colors.
        # https://learn.adafruit.com/led-tricks-gamma-correction
        for j in range(num_leds):
            (red_gamma, green_gamma, blue_gamma) = strip[j]
            red_gamma = gammas[red_gamma]
            green_gamma = gammas[green_gamma]
            blue_gamma = gammas[blue_gamma]
            strip[j] = (red_gamma, green_gamma, blue_gamma)

        strip.show()
