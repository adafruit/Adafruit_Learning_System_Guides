# SPDX-FileCopyrightText: 2018 Phillip Burgess for Adafruit Industries
#
# SPDX-License-Identifier: MIT

"""
Stomp & roar sound example for Adafruit Hallowing. Functions as a crude
pedometer, plays different sounds in response to steps & jumps. Step
detection based on "Full-Featured Pedometer Design Realized with 3-Axis
Digital Accelerometer" by Neil Zhao, Analog Dialogue Technical Journal,
June 2010.
"""

import time
import math
import digitalio
import displayio
import board
import audioio
import audiocore
import neopixel

def load_wav(name):
    """
    Load a WAV audio file into RAM.
    @param name: partial file name string, complete name will be built on
                 this, e.g. passing 'foo' will load file 'foo.wav'.
    @return WAV buffer that can be passed to play_wav() below.
    """
    return audiocore.WaveFile(open(name + '.wav', 'rb'))

STOMP_WAV = load_wav('stomp') # WAV file to play with each step
ROAR_WAV = load_wav('roar')   # WAV when jumping
IMAGEFILE = 'reptar.bmp'      # BMP image to display

IS_HALLOWING_M4 = False

# Perform a couple extra steps for the HalloWing M4
try:
    if getattr(board, "CAP_PIN"):
        IS_HALLOWING_M4 = True
    if getattr(board, "SPEAKER_ENABLE"):
        # Enable the Speaker
        speaker_enable = digitalio.DigitalInOut(board.SPEAKER_ENABLE)
        speaker_enable.direction = digitalio.Direction.OUTPUT
        speaker_enable.value = True
except AttributeError:
    pass

AUDIO = audioio.AudioOut(board.SPEAKER)  # Speaker

board.DISPLAY.auto_brightness = False

# Set up accelerometer on I2C bus, 4G range:
I2C = board.I2C()
if IS_HALLOWING_M4:
    import adafruit_msa301
    ACCEL = adafruit_msa301.MSA301(I2C)
else:
    import adafruit_lis3dh
    try:
        ACCEL = adafruit_lis3dh.LIS3DH_I2C(I2C, address=0x18) # Production board
    except ValueError:
        ACCEL = adafruit_lis3dh.LIS3DH_I2C(I2C, address=0x19) # Beta hardware
    ACCEL.range = adafruit_lis3dh.RANGE_4_G

STEP_INTERVAL_MIN = 0.3 # Shortest interval to walk one step (seconds)
STEP_INTERVAL_MAX = 2.0 # Longest interval to walk one step (seconds)
SAMPLE_RATE_HZ = 50     # Accelerometer polling frequency (per second)
WINDOW_INTERVAL = 1.0   # How often to reset window min/max range (seconds)
PRECISION = 2.0         # Lower numbers = more sensitive to steps
SAMPLE_INTERVAL = 1.0 / SAMPLE_RATE_HZ

FILTER_SIZE = 4         # Number of accelerometer readings to average
FILTER_BUF = [0] * FILTER_SIZE
FILTER_SUM = 0          # Initial average value
FILTER_INDEX = 0        # Current position in sample-averaging buffer

# Display BMP image.
try:
    board.DISPLAY.brightness = 0
    SCREEN = displayio.Group()
    board.DISPLAY.show(SCREEN)

    # CircuitPython 6 & 7 compatible
    BITMAP = displayio.OnDiskBitmap(open(IMAGEFILE, 'rb'))
    TILEGRID = displayio.TileGrid(
        BITMAP,
        pixel_shader=getattr(BITMAP, 'pixel_shader', displayio.ColorConverter())
    )

    # # CircuitPython 7+ compatible
    # BITMAP = displayio.OnDiskBitmap(IMAGEFILE)
    # TILEGRID = displayio.TileGrid(BITMAP, pixel_shader=BITMAP.pixel_shader)

    SCREEN.append(TILEGRID)
    board.DISPLAY.brightness = 1.0   # Turn on display backlight
except (OSError, ValueError):
    pass

# If everything has initialized correctly, turn off the onboard NeoPixel:
PIXEL = neopixel.NeoPixel(board.NEOPIXEL, 1, brightness=0)
PIXEL.show()

# Read initial accelerometer state and assign to various things to start
X, Y, Z = ACCEL.acceleration
MAG = math.sqrt(X * X + Y * Y + Z * Z) # 3space magnitude
WINDOW_MIN = MAG # Minimum reading from accel in last WINDOW_INTERVAL seconds
WINDOW_MAX = MAG # Maximum reading from accel in last WINDOW_INTERVAL seconds
THRESHOLD = MAG  # Midpoint of WINDOW_MIN, WINDOW_MAX
SAMPLE_OLD = MAG
SAMPLE_NEW = MAG

LAST_STEP_TIME = time.monotonic() # Time of last step detect
LAST_WINDOW_TIME = LAST_STEP_TIME # Time of last min/max window reset

while True:

    TIME = time.monotonic() # Time at start of loop

    X, Y, Z = ACCEL.acceleration           # Read accelerometer
    MAG = math.sqrt(X * X + Y * Y + Z * Z) # Calc 3space magnitude

    # Low-pass filter: average the last FILTER_SIZE magnitude readings
    FILTER_SUM -= FILTER_BUF[FILTER_INDEX]   # Subtract old value from sum
    FILTER_BUF[FILTER_INDEX] = MAG           # Store new value in buffer
    FILTER_SUM += MAG                        # Add new value to sum
    FILTER_INDEX += 1                        # Increment position in buffer
    if FILTER_INDEX >= FILTER_SIZE:          # and wrap around to start
        FILTER_INDEX = 0
    SAMPLE_RESULT = FILTER_SUM / FILTER_SIZE # Average buffer value

    if SAMPLE_RESULT < 2: # Jump detected (freefall, or close to it)
        while MAG < 10 and time.monotonic() - TIME < 1: # Wait for landing
            X, Y, Z = ACCEL.acceleration
            MAG = math.sqrt(X * X + Y * Y + Z * Z)
        AUDIO.play(ROAR_WAV)
        while AUDIO.playing:
            pass
        continue # Back to top of loop

    # Every WINDOW_INTERVAL seconds, calc new THRESHOLD, reset min and max
    if TIME - LAST_WINDOW_TIME >= WINDOW_INTERVAL: # Time for new window?
        THRESHOLD = (WINDOW_MIN + WINDOW_MAX) / 2  # Average of min & max
        WINDOW_MIN = SAMPLE_RESULT                 # Reset min and max to
        WINDOW_MAX = SAMPLE_RESULT                 # the last value read
        LAST_WINDOW_TIME = TIME                    # Note time of reset
    else:                                          # Not WINDOW_INTERVAL yet,
        if SAMPLE_RESULT < WINDOW_MIN:             # keep adjusting min and
            WINDOW_MIN = SAMPLE_RESULT             # max to accel data.
        if SAMPLE_RESULT > WINDOW_MAX:
            WINDOW_MAX = SAMPLE_RESULT

    # Watch for sufficiently large changes in accelerometer readings...
    SAMPLE_OLD = SAMPLE_NEW
    if abs(SAMPLE_RESULT - SAMPLE_OLD) > PRECISION:
        SAMPLE_NEW = SAMPLE_RESULT
        # If crossing the threshold in the + direction...
        if SAMPLE_OLD <= THRESHOLD <= SAMPLE_NEW:
            # And if within reasonable time window for another step...
            TIME_SINCE_LAST_STEP = TIME - LAST_STEP_TIME
            if STEP_INTERVAL_MIN <= TIME_SINCE_LAST_STEP <= STEP_INTERVAL_MAX:
                # It's a step!
                AUDIO.play(STOMP_WAV)
            LAST_STEP_TIME = TIME

    # Dillydally so the accelerometer isn't polled faster than desired rate
    ELAPSED = time.monotonic() - TIME
    if ELAPSED < SAMPLE_INTERVAL:
        time.sleep(SAMPLE_INTERVAL - ELAPSED)
