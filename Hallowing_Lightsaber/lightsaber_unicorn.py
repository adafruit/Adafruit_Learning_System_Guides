"""UNICORN SWORD example for Adafruit Hallowing & NeoPixel strip"""
# pylint: disable=bare-except

import time
import math
import random
import board
import busio
import audioio
import touchio
import neopixel
import adafruit_lis3dh
from neopixel_write import neopixel_write

# CUSTOMIZE SENSITIVITY HERE: smaller numbers = more sensitive to motion
HIT_THRESHOLD = 250
SWING_THRESHOLD = 125

NUM_PIXELS = 30                        # NeoPixel strip length (in pixels)
NEOPIXEL_PIN = board.EXTERNAL_NEOPIXEL # Pin where NeoPixels are connected
STRIP = neopixel.NeoPixel(NEOPIXEL_PIN, NUM_PIXELS, brightness=1, auto_write=False)
STRIP.fill(0)                          # NeoPixels off ASAP on startup
STRIP.show()
TOUCH = touchio.TouchIn(board.A2)      # Rightmost capacitive touch pad
AUDIO = audioio.AudioOut(board.A0)     # Speaker
MODE = 0                               # Initial mode = OFF
FRAMES = 10                            # Pre-calculated animation frames

# Set up accelerometer on I2C bus, 4G range:
I2C = busio.I2C(board.SCL, board.SDA)
try:
    ACCEL = adafruit_lis3dh.LIS3DH_I2C(I2C, address=0x18) # Production board
except:
    ACCEL = adafruit_lis3dh.LIS3DH_I2C(I2C, address=0x19) # Beta hardware
ACCEL.range = adafruit_lis3dh.RANGE_4_G

def hsv_to_rgb(hue, saturation, value):
    """
    Convert HSV color (hue, saturation, value) to RGB (red, green, blue)
    @param hue:        0=Red, 1/6=Yellow, 2/6=Green, 3/6=Cyan, 4/6=Blue, etc.
    @param saturation: 0.0=Monochrome to 1.0=Fully saturated
    @param value:      0.0=Black to 1.0=Max brightness
    @returns: red, green, blue eacn in range 0 to 255
    """
    hue = hue * 6.0       # Hue circle = 0.0 to 6.0
    sxt = math.floor(hue) # Sextant index is next-lower integer of hue
    frac = hue - sxt      # Fraction-within-sextant is 0.0 to <1.0
    sxt = int(sxt) % 6    # mod6 the sextant so it's always 0 to 5

    if sxt == 0: # Red to <yellow
        red, green, blue = 1.0, frac, 0.0
    elif sxt == 1: # Yellow to <green
        red, green, blue = 1.0 - frac, 1.0, 0.0
    elif sxt == 2: # Green to <cyan
        red, green, blue = 0.0, 1.0, frac
    elif sxt == 3: # Cyan to <blue
        red, green, blue = 0.0, 1.0 - frac, 1.0
    elif sxt == 4: # Blue to <magenta
        red, green, blue = frac, 0.0, 1.0
    else: # Magenta to <red
        red, green, blue = 1.0, 0.0, 1.0 - frac

    invsat = 1.0 - saturation # Inverse-of-saturation

    red = int(((red * saturation) + invsat) * value * 255.0 + 0.5)
    green = int(((green * saturation) + invsat) * value * 255.0 + 0.5)
    blue = int(((blue * saturation) + invsat) * value * 255.0 + 0.5)

    return red, green, blue

# Unlike the single-color laser sword example which can compute and fill
# the NeoPixel strip on the fly, this version is doing a bunch of color
# calculations which would slow things down too much when also trying to
# read the accelerometer.  Instead, the 'idle' color state of the sword,
# plus each of two animations (swinging and hitting) are pre-computed at
# program start and stored in bytearrays...these can be quickly issued
# to the NeoPixel strip later as needed.

IDLE = bytearray(NUM_PIXELS * STRIP.bpp)
SWING_ANIM = [bytearray(NUM_PIXELS * STRIP.bpp) for i in range(FRAMES)]
HIT_ANIM = [bytearray(NUM_PIXELS * STRIP.bpp) for i in range(FRAMES)]

IDX = 0
for PIXEL in range(NUM_PIXELS):  # For each pixel along strip...
    HUE = PIXEL / NUM_PIXELS     # 0.0 to <1.0
    RED, GREEN, BLUE = hsv_to_rgb(HUE, 1.0, 0.2)
    IDLE[IDX + STRIP.order[0]] = RED    # Store idle color for pixel
    IDLE[IDX + STRIP.order[1]] = GREEN
    IDLE[IDX + STRIP.order[2]] = BLUE
    for frame in range(FRAMES):  # For each frame of animation...
        FRAC = frame / (FRAMES - 1) # 0.0 to 1.0
        RED, GREEN, BLUE = hsv_to_rgb(HUE + FRAC, FRAC, 1.0 - 0.8 * FRAC)
        HIT_ANIM[frame][IDX + STRIP.order[0]] = RED
        HIT_ANIM[frame][IDX + STRIP.order[1]] = GREEN
        HIT_ANIM[frame][IDX + STRIP.order[2]] = BLUE
        RED, GREEN, BLUE = hsv_to_rgb(HUE + FRAC, 1.0, 1.0 - 0.8 * FRAC)
        SWING_ANIM[frame][IDX + STRIP.order[0]] = RED
        SWING_ANIM[frame][IDX + STRIP.order[1]] = GREEN
        SWING_ANIM[frame][IDX + STRIP.order[2]] = BLUE
    IDX += 3
# Go back through the hit animation and randomly set one
# pixel per frame to white to create a sparkle effect.
for frame in range(FRAMES):
    IDX = random.randint(0, NUM_PIXELS - 1) * 3
    HIT_ANIM[frame][IDX] = 255
    HIT_ANIM[frame][IDX + 1] = 255
    HIT_ANIM[frame][IDX + 2] = 255

def play_wav(name, loop=False):
    """
    Play a WAV file in the 'sounds' directory.
    @param name: partial file name string, complete name will be built around
                 this, e.g. passing 'foo' will play file 'sounds/foo.wav'.
    @param loop: if True, sound will repeat indefinitely (until interrupted
                 by another sound).
    """
    try:
        wave_file = open('sounds/' + name + '.wav', 'rb')
        wave = audioio.WaveFile(wave_file)
        AUDIO.play(wave, loop=loop)
    except:
        return

def power(sound, duration, reverse):
    """
    Animate NeoPixels with accompanying sound effect for power on / off.
    @param sound:    sound name (similar format to play_wav() above)
    @param duration: estimated duration of sound, in seconds (>0.0)
    @param reverse:  if True, do power-off effect (reverses animation)
    """
    start_time = time.monotonic()  # Save function start time
    play_wav(sound)
    while True:
        elapsed = time.monotonic() - start_time  # Time spent in function
        if elapsed > duration:                   # Past sound duration?
            break                                # Stop animating
        fraction = elapsed / duration            # Animation time, 0.0 to 1.0
        if reverse:
            fraction = 1.0 - fraction            # 1.0 to 0.0 if reverse
        fraction = math.pow(fraction, 0.5)       # Apply nonlinear curve
        threshold = int(NUM_PIXELS * fraction + 0.5)
        idx = 0
        for pixel in range(NUM_PIXELS):          # Fill NeoPixel strip
            if pixel <= threshold:
                STRIP[pixel] = (                 # BELOW threshold,
                    IDLE[idx + STRIP.order[0]],  # fill pixels with
                    IDLE[idx + STRIP.order[1]],  # IDLE pattern
                    IDLE[idx + STRIP.order[2]])
            else:
                STRIP[pixel] = 0                 # OFF pixels ABOVE threshold
            STRIP.show()
            idx += 3
    if reverse:
        STRIP.fill(0)                            # At end, ensure strip is off
        STRIP.show()
    else:
        neopixel_write(STRIP.pin, IDLE)          # or all pixels set on
    while AUDIO.playing:                         # Wait until audio done
        pass

# Main program loop, repeats indefinitely
while True:

    if TOUCH.value:                         # Capacitive pad touched?
        if MODE is 0:                       # If currently off...
            power('on', 3.0, False)         # Power up!
            play_wav('idle', loop=True)     # Play background hum sound
            MODE = 1                        # ON (idle) mode now
        else:                               # else is currently on...
            power('off', 2.0, True)        # Power down
            MODE = 0                        # OFF mode now
        while TOUCH.value:                  # Wait for button release
            time.sleep(0.2)                 # to avoid repeated triggering

    elif MODE >= 1:                         # If not OFF mode...
        ACCEL_X, ACCEL_Y, ACCEL_Z = ACCEL.acceleration # Read accelerometer
        ACCEL_SQUARED = ACCEL_X * ACCEL_X + ACCEL_Z * ACCEL_Z
        # (Y axis isn't needed for this, assuming Hallowing is mounted
        # sideways to stick.  Also, square root isn't needed, since we're
        # just comparing thresholds...use squared values instead, save math.)
        if ACCEL_SQUARED > HIT_THRESHOLD:   # Large acceleration = HIT
            TRIGGER_TIME = time.monotonic() # Save initial time of hit
            play_wav('hit')                 # Start playing 'hit' sound
            ACTIVE_ANIM = HIT_ANIM
            MODE = 3                        # HIT mode
        elif MODE is 1 and ACCEL_SQUARED > SWING_THRESHOLD: # Mild = SWING
            TRIGGER_TIME = time.monotonic() # Save initial time of swing
            play_wav('swing')               # Start playing 'swing' sound
            ACTIVE_ANIM = SWING_ANIM
            MODE = 2                        # SWING mode
        elif MODE > 1:                      # If in SWING or HIT mode...
            if AUDIO.playing:               # And sound currently playing...
                BLEND = time.monotonic() - TRIGGER_TIME # Time since triggered
                BLEND *= 0.7                # 0.0 to 1.0 in ~1.4 sec
                if MODE == 2:               # If SWING,
                    BLEND = abs(0.5 - BLEND) * 2.0 # ramp up, down
                if BLEND > 1.0:
                    BLEND = 1.0
                elif BLEND < 0.0:
                    BLEND = 0.0
                FRAME = int(BLEND * (FRAMES - 1) + 0.5)
                neopixel_write(STRIP.pin, ACTIVE_ANIM[FRAME])
            else:                           # No sound now, but still MODE > 1
                play_wav('idle', loop=True) # Resume background hum
                neopixel_write(STRIP.pin, IDLE) # Show idle pattern
                MODE = 1                    # IDLE mode now
