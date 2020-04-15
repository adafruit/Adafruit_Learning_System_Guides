import random
import time

import board
import displayio
import framebufferio
import protomatter

displayio.release_displays()

proto = protomatter.Protomatter(
    width=64, height=32, bit_depth=3,
    rgb_pins=[board.D6, board.D5, board.D9, board.D11, board.D10, board.D12],
    addr_pins=[board.A5, board.A4, board.A3, board.A2],
    clock_pin=board.D13, latch_pin=board.D0, output_enable_pin=board.D1)
display = framebufferio.FramebufferDisplay(proto, auto_refresh=False)

bitmap_file = open("emoji.bmp", 'rb')
bitmap = displayio.OnDiskBitmap(bitmap_file)

STOPPED, RUNNING, BRAKING = range(3)

def shuffled(seq):
    return sorted(seq, key=lambda _: random.random())

class Strip(displayio.TileGrid):
    def __init__(self):
        super().__init__(bitmap=bitmap, pixel_shader=displayio.ColorConverter(),
                         width=1, height=4, tile_width=20, tile_height=24)
        self.order = shuffled(range(20))
        self.state = STOPPED
        self.pos = 0
        self.vel = 0
        self.y = 0
        self.x = 0
        self.stop_time = time.monotonic_ns()

    def step(self):
        if self.state == RUNNING:
            self.vel = max(self.vel * 9 // 10, 64)
            if time.monotonic_ns() > self.stop_time:
                self.state = BRAKING
        elif self.state == BRAKING:
            self.vel = max(self.vel * 85 // 100, 7)
        self.pos = (self.pos + self.vel) % 7680
        yy = round(self.pos / 16)
        yyy = yy % 24
        off = yy // 24
        if self.state == BRAKING and self.vel == 7 and yyy < 4:
            self.pos = off * 24 * 16
            self.vel = 0
            yy = 0
            self.state = STOPPED
        self.y = yy % 24 - 20
        for i in range(4):
            self[i] = self.order[(19 - i + off) % 20]

    def kick(self, i):
        self.state = RUNNING
        self.vel = random.randint(256, 320)
        self.stop_time = time.monotonic_ns() + 3000000000 + i * 350000000

    def brake(self):
        self.state = BRAKING

g = displayio.Group(max_size=3)
strips = []
for idx in range(3):
    strip = Strip()
    strip.x = idx * 22
    strip.y = -20
    g.append(strip)
    strips.append(strip)
display.show(g)

orders = [shuffled(range(20)), shuffled(range(20)), shuffled(range(20))]

for si, oi in zip(strips, orders):
    for idx in range(4):
        si[idx] = oi[idx]

def all_stopped():
    return all(si.state == STOPPED for si in strips)

for idx, si in enumerate(strips):
    si.kick(idx)

while True:
    display.refresh(minimum_frames_per_second=0)
    if all_stopped():
        for idx in range(100):
            display.refresh(minimum_frames_per_second=0)
        for idx, si in enumerate(strips):
            si.kick(idx)

    for idx, si in enumerate(strips):
        si.step()
