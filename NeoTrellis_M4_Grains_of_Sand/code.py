# Digital sand demo uses the accelerometer to move sand particles in a
# realistic way.  Tilt the board to see the sand grains tumble around and light
# up LEDs.  Based on the code created by Phil Burgess and Dave Astels, see:
#   https://learn.adafruit.com/digital-sand-dotstar-circuitpython-edition/code
#   https://learn.adafruit.com/animated-led-sand
# Ported to NeoTrellis M4 by John Thurmond.
#
# The MIT License (MIT)
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

import math
import random
import board
import audioio
import busio
import adafruit_trellism4
import adafruit_adxl34x

N_GRAINS = 8  # Number of grains of sand
WIDTH = 8  # Display width in pixels
HEIGHT = 4  # Display height in pixels
NUMBER_PIXELS = WIDTH * HEIGHT
MAX_FPS = 20  # Maximum redraw rate, frames/second
MAX_X = WIDTH * 256 - 1
MAX_Y = HEIGHT * 256 - 1

class Grain:
    """A simple struct to hold position and velocity information
    for a single grain."""

    def __init__(self):
        """Initialize grain position and velocity."""
        self.x = 0
        self.y = 0
        self.vx = 0
        self.vy = 0

grains = [Grain() for _ in range(N_GRAINS)]

color = random.randint(1, 254) # Set a random color to start
current_press = set() # Get ready for button presses

# Set up Trellis and accelerometer
trellis = adafruit_trellism4.TrellisM4Express(rotation=0)
i2c = busio.I2C(board.ACCELEROMETER_SCL, board.ACCELEROMETER_SDA)
sensor = adafruit_adxl34x.ADXL345(i2c)

# Add tap detection - with a pretty hard tap
sensor.enable_tap_detection(threshold=50)

color_mode = 0

oldidx = 0
newidx = 0
delta = 0
newx = 0
newy = 0

occupied_bits = [False for _ in range(WIDTH * HEIGHT)]

# Add Audio file...
f = open("water-click.wav", "rb")
wav = audioio.WaveFile(f)
print("%d channels, %d bits per sample, %d Hz sample rate " %
      (wav.channel_count, wav.bits_per_sample, wav.sample_rate))
audio = audioio.AudioOut(board.A1)
#audio.play(wav)

def index_of_xy(x, y):
    """Convert an x/column and y/row into an index into
    a linear pixel array.

    :param int x: column value
    :param int y: row value
    """
    return (y >> 8) * WIDTH + (x >> 8)

def already_present(limit, x, y):
    """Check if a pixel is already used.

    :param int limit: the index into the grain array of
    the grain being assigned a pixel Only grains already
    allocated need to be checks against.
    :param int x: proposed clumn value for the new grain
    :param int y: proposed row valuse for the new grain
    """
    for j in range(limit):
        if x == grains[j].x or y == grains[j].y:
            return True
    return False

def wheel(pos):
    # Input a value 0 to 255 to get a color value.
    # The colours are a transition r - g - b - back to r.
    if pos < 0 or pos > 255:
        return 0, 0, 0
    if pos < 85:
        return int(255 - pos*3), int(pos*3), 0
    if pos < 170:
        pos -= 85
        return 0, int(255 - pos*3), int(pos*3)
    pos -= 170
    return int(pos * 3), 0, int(255 - (pos*3))

for g in grains:
    placed = False
    while not placed:
        g.x = random.randint(0, WIDTH * 256 - 1)
        g.y = random.randint(0, HEIGHT * 256 - 1)
        placed = not occupied_bits[index_of_xy(g.x, g.y)]
    occupied_bits[index_of_xy(g.x, g.y)] = True
    g.vx = 0
    g.vy = 0

while True:
    # Check for tap and adjust color mode
    if sensor.events['tap']:
        color_mode += 1
    if color_mode > 2:
        color_mode = 0

    # Display frame rendered on prior pass.  It's done immediately after the
    # FPS sync (rather than after rendering) for consistent animation timing.

    for i in range(NUMBER_PIXELS):

        # Some color options:

        # Random color every refresh
        if color_mode == 0:
            if occupied_bits[i]:
                trellis.pixels[(i%8, i//8)] = wheel(random.randint(1, 254))
            else:
                trellis.pixels[(i%8, i//8)] = (0, 0, 0)
        # Color by pixel
        if color_mode == 1:
            trellis.pixels[(i%8, i//8)] = wheel(i*2) if occupied_bits[i] else (0, 0, 0)

        # Change color to random on button press, or cycle when you hold one down
        if color_mode == 2:
            trellis.pixels[(i%8, i//8)] = wheel(color) if occupied_bits[i] else (0, 0, 0)

    # Change color to a new random color on button press
    pressed = set(trellis.pressed_keys)
    for press in pressed - current_press:
        if press:
            print("Pressed:", press)
            color = random.randint(1, 254)
            print("Color:", color)

    # Read accelerometer...
    f_x, f_y, f_z = sensor.acceleration

    # I had to manually scale these to get them in the -128 to 128 range-ish - should be done better
    f_x = int(f_x * 9.80665 * 16704/1000)
    f_y = int(f_y * 9.80665 * 16704/1000)
    f_z = int(f_z * 9.80665 * 16704/1000)

    ax = f_x >> 3  # Transform accelerometer axes
    ay = f_y >> 3  # to grain coordinate space
    az = abs(f_z) >> 6  # Random motion factor

    print("%6d %6d %6d"%(ax,ay,az))
    az = 1 if (az >= 3) else (4 - az)  # Clip & invert
    ax -= az  # Subtract motion factor from X, Y
    ay -= az
    az2 = (az << 1) + 1  # Range of random motion to add back in

    # Adjust axes for the NeoTrellis M4 (reuses code above rather than fixing it - inefficient)
    ax2 = ax
    ax = -ay
    ay = ax2

    # ...and apply 2D accel vector to grain velocities...
    v2 = 0  # Velocity squared
    v = 0.0  # Absolute velociy
    for g in grains:

        g.vx += ax + random.randint(0, az2)  # A little randomness makes
        g.vy += ay + random.randint(0, az2)  # tall stacks topple better!

        # Terminal velocity (in any direction) is 256 units -- equal to
        # 1 pixel -- which keeps moving grains from passing through each other
        # and other such mayhem.  Though it takes some extra math, velocity is
        # clipped as a 2D vector (not separately-limited X & Y) so that
        # diagonal movement isn't faster

        v2 = g.vx * g.vx + g.vy * g.vy
        if v2 > 65536:  # If v^2 > 65536, then v > 256
            v = math.floor(math.sqrt(v2))  # Velocity vector magnitude
            g.vx = (g.vx // v) << 8  # Maintain heading
            g.vy = (g.vy // v) << 8  # Limit magnitude

    # ...then update position of each grain, one at a time, checking for
    # collisions and having them react.  This really seems like it shouldn't
    # work, as only one grain is considered at a time while the rest are
    # regarded as stationary.  Yet this naive algorithm, taking many not-
    # technically-quite-correct steps, and repeated quickly enough,
    # visually integrates into something that somewhat resembles physics.
    # (I'd initially tried implementing this as a bunch of concurrent and
    # "realistic" elastic collisions among circular grains, but the
    # calculations and volument of code quickly got out of hand for both
    # the tiny 8-bit AVR microcontroller and my tiny dinosaur brain.)

    for g in grains:
        newx = g.x + g.vx  # New position in grain space
        newy = g.y + g.vy
        if newx > MAX_X:  # If grain would go out of bounds
            newx = MAX_X  # keep it inside, and
            g.vx //= -2  # give a slight bounce off the wall
        elif newx < 0:
            newx = 0
            g.vx //= -2
        if newy > MAX_Y:
            newy = MAX_Y
            g.vy //= -2
        elif newy < 0:
            newy = 0
            g.vy //= -2

        oldidx = index_of_xy(g.x, g.y)  # prior pixel
        newidx = index_of_xy(newx, newy)  # new pixel
        # If grain is moving to a new pixel...
        if oldidx != newidx and occupied_bits[newidx]:
            # but if that pixel is already occupied...
            # What direction when blocked?
            delta = abs(newidx - oldidx)
            if delta == 1:  # 1 pixel left or right
                newx = g.x  # cancel x motion
                # and bounce X velocity (Y is ok)
                g.vx //= -2
                newidx = oldidx  # no pixel change
            elif delta == WIDTH:  # 1 pixel up or down
                newy = g.y  # cancel Y motion
                # and bounce Y velocity (X is ok)
                g.vy //= -2
                newidx = oldidx  # no pixel change
            else:  # Diagonal intersection is more tricky...
                # Try skidding along just one axis of motion if
                # possible (start w/ faster axis). Because we've
                # already established that diagonal (both-axis)
                # motion is occurring, moving on either axis alone
                # WILL change the pixel index, no need to check
                # that again.
                if abs(g.vx) > abs(g.vy):  # x axis is faster
                    newidx = index_of_xy(newx, g.y)
                    # that pixel is free, take it! But...
                    if not occupied_bits[newidx]:
                        newy = g.y  # cancel Y motion
                        g.vy //= -2  # and bounce Y velocity
                    else:  # X pixel is taken, so try Y...
                        newidx = index_of_xy(g.x, newy)
                        # Pixel is free, take it, but first...
                        if not occupied_bits[newidx]:
                            newx = g.x  # Cancel X motion
                            g.vx //= -2  # Bounce X velocity
                        else:  # both spots are occupied
                            newx = g.x  # Cancel X & Y motion
                            newy = g.y
                            g.vx //= -2  # Bounce X & Y velocity
                            g.vy //= -2
                            newidx = oldidx  # Not moving
                else:  # y axis is faster. start there
                    newidx = index_of_xy(g.x, newy)
                    # Pixel's free! Take it! But...
                    if not occupied_bits[newidx]:
                        newx = g.x  # Cancel X motion
                        g.vx //= -2  # Bounce X velocity
                    else:  # Y pixel is taken, so try X...
                        newidx = index_of_xy(newx, g.y)
                        # Pixel is free, take it, but first...
                        if not occupied_bits[newidx]:
                            newy = g.y  # cancel Y motion
                            g.vy //= -2  # and bounce Y velocity
                        else:  # both spots are occupied
                            newx = g.x  # Cancel X & Y motion
                            newy = g.y
                            g.vx //= -2  # Bounce X & Y velocity
                            g.vy //= -2
                            newidx = oldidx  # Not moving
        occupied_bits[oldidx] = False
        occupied_bits[newidx] = True
        if oldidx != newidx:
            audio.play(wav) # If there's an update, play the sound
        g.x = newx
        g.y = newy
