# SPDX-FileCopyrightText: 2018 Phillip Burgess for Adafruit Industries
#
# SPDX-License-Identifier: MIT

"""
Jump & touch sound example for Adafruit Hallowing. Plays different sounds
in response to jumping and capacitive touch pads.
"""

import time
import board
import digitalio
import displayio
import audioio
import audiocore
import touchio
import neopixel

def load_wav(name):
    """
    Load a WAV audio file into RAM.
    @param name: partial file name string, complete name will be built on
                 this, e.g. passing 'foo' will load file 'foo.wav'.
    @return WAV buffer that can be passed to play_wav() below.
    """
    return audiocore.WaveFile(open(name + '.wav', 'rb'))

def play_wav(wav):
    """
    Play a WAV file previously loaded with load_wav(). This function
    "blocks," i.e. does not return until the sound is finished playing.
    @param wav: WAV buffer previously returned by load_wav() function.
    """
    AUDIO.play(wav)      # Begin WAV playback
    while AUDIO.playing: # Keep idle here as long as it plays
        pass
    time.sleep(1)        # A small pause avoids repeated triggering

TOUCH_WAV = load_wav('touch') # WAV file to play when capacitive pads touched
JUMP_WAV = load_wav('jump')   # WAV file to play when jumping
JUMP_THRESHOLD = 4.0          # Higher number = triggers more easily
IMAGEFILE = 'mario.bmp'       # BMP image to display

IS_HALLOWING_M4 = False

# Perform a couple extra steps for the HalloWing M4
try:
    if getattr(board, "CAP_PIN"):
        IS_HALLOWING_M4 = True
        # Create digitalio objects and pull low for HalloWing M4
        cap_pin = digitalio.DigitalInOut(board.CAP_PIN)
        cap_pin.direction = digitalio.Direction.OUTPUT
        cap_pin.value = False
    if getattr(board, "SPEAKER_ENABLE"):
        # Enable the Speaker
        speaker_enable = digitalio.DigitalInOut(board.SPEAKER_ENABLE)
        speaker_enable.direction = digitalio.Direction.OUTPUT
        speaker_enable.value = True
except AttributeError:
    pass

AUDIO = audioio.AudioOut(board.SPEAKER)  # Speaker

try:
    board.DISPLAY.auto_brightness = False
except AttributeError:
    pass
TOUCH1 = touchio.TouchIn(board.TOUCH1)  # Capacitive touch pads
TOUCH2 = touchio.TouchIn(board.TOUCH2)
TOUCH3 = touchio.TouchIn(board.TOUCH3)
TOUCH4 = touchio.TouchIn(board.TOUCH4)

# Set up accelerometer on I2C bus, 4G range:
i2c = board.I2C()  # uses board.SCL and board.SDA
# i2c = board.STEMMA_I2C()  # For using the built-in STEMMA QT connector on a microcontroller
if IS_HALLOWING_M4:
    import adafruit_msa301
    ACCEL = adafruit_msa301.MSA301(i2c)
else:
    import adafruit_lis3dh
    try:
        ACCEL = adafruit_lis3dh.LIS3DH_I2C(i2c, address=0x18) # Production board
    except ValueError:
        ACCEL = adafruit_lis3dh.LIS3DH_I2C(i2c, address=0x19) # Beta hardware
    ACCEL.range = adafruit_lis3dh.RANGE_4_G

try:
    board.DISPLAY.brightness = 0
    SCREEN = displayio.Group()
    board.DISPLAY.root_group = SCREEN

    # CircuitPython 7+ compatible
    BITMAP = displayio.OnDiskBitmap(IMAGEFILE)
    TILEGRID = displayio.TileGrid(BITMAP, pixel_shader=BITMAP.pixel_shader)

    SCREEN.append(TILEGRID)
    board.DISPLAY.brightness = 1.0   # Turn on display backlight
except (OSError, ValueError):
    pass

# If everything has initialized correctly, turn off the onboard NeoPixel:
PIXEL = neopixel.NeoPixel(board.NEOPIXEL, 1, brightness=0)
PIXEL.show()

while True:
    # No freefall detect in LIS3DH library, but it's easily done manually...
    # poll the accelerometer and look for near-zero readings on all axes.
    X, Y, Z = ACCEL.acceleration
    A2 = X * X + Y * Y + Z * Z  # Acceleration^2 in 3space (no need for sqrt)
    if A2 < JUMP_THRESHOLD:
        # Freefall (or very close to it) detected, play a sound:
        play_wav(JUMP_WAV)
    elif TOUCH1.value or TOUCH2.value or TOUCH3.value or TOUCH4.value:
        # One of the capacitive pads was touched, play other sound:
        play_wav(TOUCH_WAV)
