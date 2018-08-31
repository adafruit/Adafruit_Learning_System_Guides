"""Lightsager for Adafruit Hallowing & NeoPixel strip"""

import time
import math
import audioio
import busio
import board
import touchio
import neopixel
import adafruit_lis3dh

# CUSTOMIZE YOUR COLOR HERE: # (red, green, blue) -- each 0 (off) to 255 (brightest)
COLOR = (0, 100, 255)  # Jedi blue
#COLOR = (255, 0, 0)  # Sith red
#COLOR = (200, 0, 150)  # pink

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

# Play a WAV file in the 'sounds' directory.  Only partial name
# is needed, e.g. passing 'foo' will play file 'sounds/foo.wav'.
# Optionally pass True as second argument to repeat indefinitely
# (until interrupted by another sound).
def play_wav(name, loop=False):
    try:
        wave_file = open('sounds/' + name + '.wav', 'rb')
        wave = audioio.WaveFile(wave_file)
        AUDIO.play(wave, loop=loop)
    except:
        return

# Animate NeoPixels with accompanying sound effect for power on / off.
# Pass sound name (similar format to play_wav() above), estimated duration
# of sound, and True if this is a power-off effect (reverses animation).
def power(sound, duration, reverse):
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

# Blend between two colors (each passed as an (r,g,b) tuple) with a given
# ratio, where 0.0 = first color, 1.0 = second color, 0.5 = 50/50 mix.
# Returns a new (r,g,b) tuple.
def mix(color1, color2, w2):
    if w2 < 0.0:
        w2 = 0.0
    elif w2 > 1.0:
        w2 = 1.0
    w1 = 1.0 - w2
    return (int(color1[0] * w1 + color2[0] * w2),
            int(color1[1] * w1 + color2[1] * w2),
            int(color1[2] * w1 + color2[2] * w2))

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
        x, y, z = ACCEL.acceleration        # Read accelerometer
        a2 = x * x + z * z                  # X & Z axis amplitude squared
        # (Y axis isn't needed for this, assuming Hallowing is mounted
        # sideways to stick.  Also, square root isn't needed, since we're
        # just comparing thresholds...use squared values instead, save math.)
        if a2 > HIT_THRESHOLD:              # Large acceleration = HIT
            start_time = time.monotonic()   # Save initial time of hit
            play_wav('hit')                 # Start playing 'hit' sound
            color = COLOR_HIT               # Set color to fade from
            MODE = 3                        # HIT mode
        elif MODE is 1 and a2 > SWING_THRESHOLD: # Mild acceleration = SWING
            start_time = time.monotonic()   # Save initial time of swing
            play_wav('swing')               # Start playing 'swing' sound
            color = COLOR_SWING             # Set color to fade from
            MODE = 2                        # SWING mode
        elif MODE > 1:                      # If in SWING or HIT mode...
            if AUDIO.playing:               # And sound currently playing...
                elapsed = time.monotonic() - start_time # Time since triggered
                c2 = mix(color, COLOR_IDLE, elapsed)    # Fade color to idle
                STRIP.fill(c2)
                STRIP.show()
            else:                           # No sound now, but still MODE > 1
                play_wav('idle', loop=True) # Resume background hum
                STRIP.fill(COLOR_IDLE)      # Set to idle color
                STRIP.show()
                MODE = 1                    # IDLE mode now
