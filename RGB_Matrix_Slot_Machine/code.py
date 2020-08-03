import random
import time

import adafruit_imageload.bmp
import audioio
import audiomp3
import board
import displayio
import digitalio
import framebufferio
import rgbmatrix

displayio.release_displays()

matrix = rgbmatrix.RGBMatrix(
    width=64, height=32, bit_depth=4,
    rgb_pins=[board.D6, board.D5, board.D9, board.D11, board.D10, board.D12],
    addr_pins=[board.A5, board.A4, board.A3, board.A2],
    clock_pin=board.D13, latch_pin=board.D0, output_enable_pin=board.D1)
display = framebufferio.FramebufferDisplay(matrix, auto_refresh=False)

# Each wheel can be in one of three states:
STOPPED, RUNNING, BRAKING = range(3)

# Return a duplicate of the input list in a random (shuffled) order.
def shuffled(seq):
    return sorted(seq, key=lambda _: random.random())

# The Wheel class manages the state of one wheel. "pos" is a position in
# floating point coordinates, with one 1 pixel being 1 position.
# The wheel also has a velocity (in positions
# per tick) and a state (one of the above constants)
class Wheel(displayio.TileGrid):
    def __init__(self, bitmap, palette):
        # Portions of up to 3 tiles are visible.
        super().__init__(bitmap=bitmap, pixel_shader=palette,
                         width=1, height=3, tile_width=20, tile_height=24)
        self.order = shuffled(range(20))
        self.state = STOPPED
        self.pos = 0
        self.vel = 0
        self.termvel = 2
        self.y = 0
        self.x = 0
        self.stop_time = time.monotonic_ns()
        self.step()

    def step(self):
        # Update each wheel for one time step
        if self.state == RUNNING:
            # Slowly lose speed when running, but go at least terminal velocity
            self.vel = max(self.vel * .99, self.termvel)
            if time.monotonic_ns() > self.stop_time:
                self.state = BRAKING
        elif self.state == BRAKING:
            # More quickly lose speed when baking, down to speed 0.4
            self.vel = max(self.vel * .85, 0.4)

        # Advance the wheel according to the velocity, and wrap it around
        # after 24*20 positions
        self.pos = (self.pos + self.vel) % (20*24)

        # Compute the rounded Y coordinate
        yy = round(self.pos)
        # Compute the offset of the tile (tiles are 24 pixels tall)
        yyy = yy % 24
        # Find out which tile is the top tile
        off = yy // 24

        # If we're braking and a tile is close to midscreen,
        # then stop and make sure that tile is exactly centered
        if self.state == BRAKING and self.vel <= 2 and yyy < 8:
            self.pos = off * 24
            self.vel = 0
            yyy = 0
            self.state = STOPPED

        # Move the displayed tiles to the correct height and make sure the
        # correct tiles are displayed.
        self.y = yyy - 20
        for i in range(3):
            self[i] = self.order[(19 - i + off) % 20]

    # Set the wheel running again, using a slight bit of randomness.
    # The 'i' value makes sure the first wheel brakes first, the second
    # brakes second, and the third brakes third.
    def kick(self, i):
        self.state = RUNNING
        self.vel = random.uniform(8, 10)
        self.termvel = random.uniform(1.8, 4.2)
        self.stop_time = time.monotonic_ns() + 3000000000 + i * 350000000


# This bitmap contains the emoji we're going to use. It is assumed
# to contain 20 icons, each 20x24 pixels. This fits nicely on the 64x32
# RGB matrix display.
the_bitmap, the_palette = adafruit_imageload.load(
    "/emoji.bmp",
    bitmap=displayio.Bitmap,
    palette=displayio.Palette)

# Our fruit machine has 3 wheels, let's create them with a correct horizontal
# (x) offset and arbitrary vertical (y) offset.
g = displayio.Group(max_size=3)
wheels = []
for idx in range(3):
    wheel = Wheel(the_bitmap, the_palette)
    wheel.x = idx * 22
    wheel.y = -20
    g.append(wheel)
    wheels.append(wheel)
display.show(g)

# We want a digital input to trigger the fruit machine
button = digitalio.DigitalInOut(board.A1)
button.switch_to_input(pull=digitalio.Pull.UP)

# Enable the speaker
enable = digitalio.DigitalInOut(board.D4)
enable.switch_to_output(True)

mp3file = open("/triangles-loop.mp3", "rb")
sample = audiomp3.MP3Decoder(mp3file)

# Play the sample (just loop it for now)
speaker = audioio.AudioOut(board.A0)
speaker.play(sample, loop=True)

# Here's the main loop
while True:
    # Refresh the dislpay (doing this manually ensures the wheels move
    # together, not at different times)
    display.refresh(minimum_frames_per_second=0, target_frames_per_second=60)

    all_stopped = all(si.state == STOPPED for si in wheels)
    if all_stopped:
        # Once everything comes to a stop, wait until the lever is pulled and
        # start everything over again.  Maybe you want to check if the
        # combination is a "winner" and add a light show or something.

        while button.value:
            pass
        for idx, si in enumerate(wheels):
            si.kick(idx)

    # Otherwise, let the wheels keep spinning...
    for idx, si in enumerate(wheels):
        si.step()
