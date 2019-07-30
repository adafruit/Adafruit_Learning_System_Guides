"""
Stomp & roar sound example for Adafruit Hallowing. Functions as a crude
pedometer, plays different sounds in response to steps & jumps. Step
detection based on "Full-Featured Pedometer Design Realized with 3-Axis
Digital Accelerometer" by Neil Zhao, Analog Dialogue Technical Journal,
June 2010.
Image display requires CircuitPython 4.0.0-alpha1 or later (with displayio
support). WILL work with earlier versions, just no image shown!
"""

import time
import math
import board
import busio
import audioio
import pulseio
import neopixel
import adafruit_lis3dh

def load_wav(name):
    """
    Load a WAV audio file into RAM.
    @param name: partial file name string, complete name will be built on
                 this, e.g. passing 'foo' will load file 'foo.wav'.
    @return WAV buffer that can be passed to play_wav() below.
    """
    return audioio.WaveFile(open(name + '.wav', 'rb'))

STOMP_WAV = load_wav('stomp') # WAV file to play with each step
ROAR_WAV = load_wav('roar')   # WAV when jumping
IMAGEFILE = 'reptar.bmp'      # BMP image to display

AUDIO = audioio.AudioOut(board.A0)              # Speaker
BACKLIGHT = pulseio.PWMOut(board.TFT_BACKLIGHT) # Display backlight

# Set up accelerometer on I2C bus, 4G range:
I2C = busio.I2C(board.SCL, board.SDA)
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

# Display BMP image. If this fails, it's not catastrophic (probably just
# older CircuitPython) and the code will continue with the step detection.
try:
    import displayio
    SCREEN = displayio.Group()
    board.DISPLAY.show(SCREEN)
    BITMAP = displayio.OnDiskBitmap(open(IMAGEFILE, 'rb'))
    SCREEN.append(
        displayio.Sprite(BITMAP,
                         pixel_shader=displayio.ColorConverter(),
                         position=(0, 0)))
    board.DISPLAY.wait_for_frame() # Wait for the image to load.
    BACKLIGHT.duty_cycle = 65535   # Turn on display backlight
except (ImportError, NameError, AttributeError) as err:
    pass # Probably earlier CircuitPython; no displayio support

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
