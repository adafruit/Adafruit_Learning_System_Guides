"""LASER SWORD (pew pew) example for Adafruit Hallowing & NeoPixel strip"""
# pylint: disable=bare-except

import time
import math
import audioio
import busio
import board
import touchio
import neopixel
import adafruit_lis3dh

# CUSTOMIZE YOUR COLOR HERE:
# (red, green, blue) -- each 0 (off) to 255 (brightest)
COLOR = (0, 100, 255)  # jedi
#COLOR = (255, 0, 0)  # sith

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

# Set up accelerometer on I2C bus, 4G range:
I2C = busio.I2C(board.SCL, board.SDA)
try:
    ACCEL = adafruit_lis3dh.LIS3DH_I2C(I2C, address=0x18) # Production board
except:
    ACCEL = adafruit_lis3dh.LIS3DH_I2C(I2C, address=0x19) # Beta hardware
ACCEL.range = adafruit_lis3dh.RANGE_4_G

# "Idle" color is 1/4 brightness, "swinging" color is full brightness...
COLOR_IDLE = (int(COLOR[0] / 4), int(COLOR[1] / 4), int(COLOR[2] / 4))
COLOR_SWING = COLOR
COLOR_HIT = (255, 255, 255)  # "hit" color is white

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
        for pixel in range(NUM_PIXELS):          # Fill NeoPixel strip
            if pixel <= threshold:
                STRIP[pixel] = COLOR_IDLE        # ON pixels BELOW threshold
            else:
                STRIP[pixel] = 0                 # OFF pixels ABOVE threshold
            STRIP.show()
    if reverse:
        STRIP.fill(0)                            # At end, ensure strip is off
    else:
        STRIP.fill(COLOR_IDLE)                   # or all pixels set on
    STRIP.show()
    while AUDIO.playing:                         # Wait until audio done
        pass

def mix(color_1, color_2, weight_2):
    """
    Blend between two colors with a given ratio.
    @param color_1:  first color, as an (r,g,b) tuple
    @param color_2:  second color, as an (r,g,b) tuple
    @param weight_2: Blend weight (ratio) of second color, 0.0 to 1.0
    @return: (r,g,b) tuple, blended color
    """
    if weight_2 < 0.0:
        weight_2 = 0.0
    elif weight_2 > 1.0:
        weight_2 = 1.0
    weight_1 = 1.0 - weight_2
    return (int(color_1[0] * weight_1 + color_2[0] * weight_2),
            int(color_1[1] * weight_1 + color_2[1] * weight_2),
            int(color_1[2] * weight_1 + color_2[2] * weight_2))

# Main program loop, repeats indefinitely
while True:

    if TOUCH.value:                         # Capacitive pad touched?
        if MODE is 0:                       # If currently off...
            power('on', 1.7, False)         # Power up!
            play_wav('idle', loop=True)     # Play background hum sound
            MODE = 1                        # ON (idle) mode now
        else:                               # else is currently on...
            power('off', 1.15, True)        # Power down
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
            COLOR_ACTIVE = COLOR_HIT        # Set color to fade from
            MODE = 3                        # HIT mode
        elif MODE is 1 and ACCEL_SQUARED > SWING_THRESHOLD: # Mild = SWING
            TRIGGER_TIME = time.monotonic() # Save initial time of swing
            play_wav('swing')               # Start playing 'swing' sound
            COLOR_ACTIVE = COLOR_SWING      # Set color to fade from
            MODE = 2                        # SWING mode
        elif MODE > 1:                      # If in SWING or HIT mode...
            if AUDIO.playing:               # And sound currently playing...
                BLEND = time.monotonic() - TRIGGER_TIME # Time since triggered
                if MODE == 2:               # If SWING,
                    BLEND = abs(0.5 - BLEND) * 2.0 # ramp up, down
                STRIP.fill(mix(COLOR_ACTIVE, COLOR_IDLE, BLEND))
                STRIP.show()
            else:                           # No sound now, but still MODE > 1
                play_wav('idle', loop=True) # Resume background hum
                STRIP.fill(COLOR_IDLE)      # Set to idle color
                STRIP.show()
                MODE = 1                    # IDLE mode now
