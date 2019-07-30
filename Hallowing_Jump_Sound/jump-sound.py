"""
Jump & touch sound example for Adafruit Hallowing. Plays different sounds
in response to jumping and capacitive touch pads.
Image display requires CircuitPython 4.0.0-alpha1 or later (with displayio
support). WILL work with earlier versions, just no image shown!
"""

import time
import pulseio
import audioio
import busio
import board
import touchio
import adafruit_lis3dh
import neopixel

def load_wav(name):
    """
    Load a WAV audio file into RAM.
    @param name: partial file name string, complete name will be built on
                 this, e.g. passing 'foo' will load file 'foo.wav'.
    @return WAV buffer that can be passed to play_wav() below.
    """
    return audioio.WaveFile(open(name + '.wav', 'rb'))

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

AUDIO = audioio.AudioOut(board.A0)              # Speaker
BACKLIGHT = pulseio.PWMOut(board.TFT_BACKLIGHT) # Display backlight
TOUCH1 = touchio.TouchIn(board.A2)              # Capacitive touch pads
TOUCH2 = touchio.TouchIn(board.A3)
TOUCH3 = touchio.TouchIn(board.A4)
TOUCH4 = touchio.TouchIn(board.A5)

# Set up accelerometer on I2C bus, 4G range:
I2C = busio.I2C(board.SCL, board.SDA)
try:
    ACCEL = adafruit_lis3dh.LIS3DH_I2C(I2C, address=0x18) # Production board
except ValueError:
    ACCEL = adafruit_lis3dh.LIS3DH_I2C(I2C, address=0x19) # Beta hardware
ACCEL.range = adafruit_lis3dh.RANGE_4_G

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
