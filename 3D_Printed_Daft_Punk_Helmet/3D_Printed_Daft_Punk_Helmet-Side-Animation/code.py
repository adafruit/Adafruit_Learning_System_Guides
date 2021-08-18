# Adafruit Trinket+NeoPixel animation for Daft Punk-inspired helmet.
# Contains some ATtiny85-specific stuff; won't run as-is on Uno, etc.

# Operates in HSV (hue, saturation, value) colorspace rather than RGB.
# Animation is an interference pattern between two waves; one controls
# saturation, the other controls value (brightness).  The wavelength,
# direction, speed and type (square vs triangle wave) for each is randomly
# selected every few seconds.  Hue is always linear, but other parameters
# are similarly randomized.

import random
import board
import neopixel
from analogio import AnalogIn

n_leds = 29             # number of LEDs per horn
led_pin = board.D0      # which pin your pixels are connected to

# initialize neopixel strip
pixels = neopixel.NeoPixel(led_pin, n_leds, brightness=1, auto_write=False)
count = 1               # countdown to next animation change

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

# initialize 3D list
wave = [0] * 5, [0] * 5, [0] * 5

wave_type = 0   # 0 = square wave, 1 = triangle wave
value_frame = 1 # start-of-frame value
value_pixel = 2 # pixel-to-pixel value
inc_frame = 3   # frame-to-frame increment
inc_pixel = 4   # pixel-to-pixel inc

wave_h = 0      # hue
wave_s = 1      # saturation
wave_v = 2      # brightness

# Random number generator is seeded from an unused 'floating'
# analog input - this helps ensure the random color choices
# aren't always the same order.
pin = AnalogIn(board.A0)
random.seed(pin.value)
pin.deinit()

# generate a non-zero random number for frame and pixel increments
def nz_random():
    random_number = 0

    while random_number <= 0:
        random_number = random.randint(0,15) - 7

    return random_number

while True:

    w = i = n = s = v = r = g = b = v1 = s1 = 0

    if count <= 0:                                  # time for new animation
        count = 250 + random.randint(0,250)         # effect run for 5-10 sec.

        for w in range(3):                          # three waves (H,S,V)
            wave[w][wave_type] = random.randint(0,2)# square vs triangle
            wave[w][inc_frame] = nz_random()        # frame increment
            wave[w][inc_pixel] = nz_random()        # pixel increment
            wave[w][value_pixel] = wave[w][value_frame]

        wave[wave_s][inc_pixel] *= 16               # make saturation & value
        wave[wave_v][inc_pixel] *= 16               # blinkier along strip

    else:                                           # continue animation
        count -= 1
        for w in range(3):
            wave[w][value_frame] += wave[w][inc_frame]
            wave[w][value_pixel] = wave[w][value_frame]

    # Render current animation frame.  COGNITIVE HAZARD: fixed point math.
    for i in range(n_leds):                             # for each LED along strip...
        # Coarse (8-bit) HSV-to-RGB conversion, hue first:
        n = (wave[wave_h][value_pixel] % 43) * 6   # angle within sextant

        sextant = wave[wave_h][value_pixel] / 43        # sextant number 0-5

        # R to Y
        if sextant == 0:
            r = 255
            g = n
            b = 0
        # Y to G
        elif sextant == 1:
            r = 254 - n
            g = 255
            b = 0
        # G to C
        elif sextant == 2:
            r = 0
            g = 255
            b = n
        # C to B
        elif sextant == 3:
            r = 0
            g = 254 - n
            b = 255
        # B to M
        elif sextant == 4:
            r = n
            g = 0
            b = 255
        # M to R
        else:
            r = 255
            g = 0
            b = 254 - n

        # Saturation = 1-256 to allow >>8 instead of /255
        s = wave[wave_s][value_pixel]

        if wave[wave_s][wave_type]:     # triangle wave?
            if s & 0x80:                # downslope
                s = (s & 0x7F) << 1
                s1 = 256 - s
            else:                       # upslope
                s = s<<1
                s1 = 1 + s
                s = 255 - s
        else:
            if s & 0x80:                # square wave
                s1 = 256                # 100% saturation
                s = 0
            else:                       # 0% saturation
                s1 = 1
                s = 255

        # Value (brightness) = 1-256 for similar reasons
        v = wave[wave_v][value_pixel]

        # value (brightness) = 1-256 for similar reasons
        if wave[wave_v][wave_type]:     # triangle wave?
            if v & 0x80:                # downslope
                v1 = 64 - ((v & 0x7F) << 1)
            else:                       # upslope
                v1 = 1 + (v << 1)
        else:
            if v & 0x80:                # square wave; on/off
                v1 = 256
            else:
                v1 = 1

        # gamma rgb values
        gr = ((((r * s1) >> 8) + s) * v1) >> 8
        gg = ((((g * s1) >> 8) + s) * v1) >> 8
        gb = ((((b * s1) >> 8) + s) * v1) >> 8

        # gamma rgb indices range check
        if -256 < gr < 256:
            r = gamma[gr]

        if -256 < gg < 256:
            g = gamma[gg]

        if -256 < gb < 256:
            b = gamma[gb]

        pixels[i] = (r, g, b)

        # update wave values along length of strip (values may wrap, is OK!)
        for w in range(3):
            wave[w][value_pixel] += wave[w][inc_pixel]

    pixels.show()
