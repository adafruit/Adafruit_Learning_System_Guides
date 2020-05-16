import random
import time

import board
import displayio
import framebufferio
import rgbmatrix

displayio.release_displays()

matrix = rgbmatrix.RGBMatrix(
    width=64, height=32, bit_depth=3,
    rgb_pins=[board.D6, board.D5, board.D9, board.D11, board.D10, board.D12],
    addr_pins=[board.A5, board.A4, board.A3, board.A2],
    clock_pin=board.D13, latch_pin=board.D0, output_enable_pin=board.D1)
display = framebufferio.FramebufferDisplay(matrix, auto_refresh=False)

# This bitmap contains the emoji we're going to use. It is assumed
# to contain 20 icons, each 20x24 pixels. This fits nicely on the 64x32
# RGB matrix display.
bitmap_file = open("emoji.bmp", 'rb')
bitmap = displayio.OnDiskBitmap(bitmap_file)

# Each wheel can be in one of three states:
STOPPED, RUNNING, BRAKING = range(3)

# Return a duplicate of the input list in a random (shuffled) order.
def shuffled(seq):
    return sorted(seq, key=lambda _: random.random())

# The Wheel class manages the state of one wheel. "pos" is a position in
# scaled integer coordinates, with one revolution being 7680 positions
# and 1 pixel being 16 positions. The wheel also has a velocity (in positions
# per tick) and a state (one of the above constants)
class Wheel(displayio.TileGrid):
    def __init__(self):
        # Portions of up to 3 tiles are visible.
        super().__init__(bitmap=bitmap, pixel_shader=displayio.ColorConverter(),
                         width=1, height=3, tile_width=20)
        self.order = shuffled(range(20))
        self.state = STOPPED
        self.pos = 0
        self.vel = 0
        self.y = 0
        self.x = 0
        self.stop_time = time.monotonic_ns()

    def step(self):
        # Update each wheel for one time step
        if self.state == RUNNING:
            # Slowly lose speed when running, but go at least speed 64
            self.vel = max(self.vel * 9 // 10, 64)
            if time.monotonic_ns() > self.stop_time:
                self.state = BRAKING
        elif self.state == BRAKING:
            # More quickly lose speed when baking, down to speed 7
            self.vel = max(self.vel * 85 // 100, 7)

        # Advance the wheel according to the velocity, and wrap it around
        # after 7680 positions
        self.pos = (self.pos + self.vel) % 7680

        # Compute the rounded Y coordinate
        yy = round(self.pos / 16)
        # Compute the offset of the tile (tiles are 24 pixels tall)
        yyy = yy % 24
        # Find out which tile is the top tile
        off = yy // 24

        # If we're braking and a tile is close to midscreen,
        # then stop and make sure that tile is exactly centered
        if self.state == BRAKING and self.vel == 7 and yyy < 4:
            self.pos = off * 24 * 16
            self.vel = 0
            yy = 0
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
        self.vel = random.randint(256, 320)
        self.stop_time = time.monotonic_ns() + 3000000000 + i * 350000000

# Our fruit machine has 3 wheels, let's create them with a correct horizontal
# (x) offset and arbitrary vertical (y) offset.
g = displayio.Group(max_size=3)
wheels = []
for idx in range(3):
    wheel = Wheel()
    wheel.x = idx * 22
    wheel.y = -20
    g.append(wheel)
    wheels.append(wheel)
display.show(g)

# Make a unique order of the emoji on each wheel
orders = [shuffled(range(20)), shuffled(range(20)), shuffled(range(20))]

# And put up some images to start with
for si, oi in zip(wheels, orders):
    for idx in range(3):
        si[idx] = oi[idx]

# We want a way to check if all the wheels are stopped
def all_stopped():
    return all(si.state == STOPPED for si in wheels)

# To start with, though, they're all in motion
for idx, si in enumerate(wheels):
    si.kick(idx)

# Here's the main loop
while True:
    # Refresh the dislpay (doing this manually ensures the wheels move
    # together, not at different times)
    display.refresh(minimum_frames_per_second=0)
    if all_stopped():
        # Once everything comes to a stop, wait a little bit and then
        # start everything over again.  Maybe you want to check if the
        # combination is a "winner" and add a light show or something.
        for idx in range(100):
            display.refresh(minimum_frames_per_second=0)
        for idx, si in enumerate(wheels):
            si.kick(idx)

    # Otherwise, let the wheels keep spinning...
    for idx, si in enumerate(wheels):
        si.step()
