from _pixelbuf import wheel
import random
import time
import array
import terminalio
import Protomatter
import displayio
from microcontroller.pin import *
displayio.release_displays()

p = Protomatter.protomatter_display(width=64, bit_depth=5,
    rgb_pins=[PA18, PA16, PA19, PA21, PA20, PA22],
    addr_pins=[PA06, PA04, PB09, PB08],
    clock_pin=PA23, latch_pin=PB17, output_enable_pin=PB16, auto_refresh=False)

bitmap_file = open("emoji.bmp", 'rb')
bitmap = displayio.OnDiskBitmap(bitmap_file)

STOPPED, RUNNING, BRAKING = range(3)

def shuffled(seq):
    return sorted(seq, key=lambda _: random.random())

class Strip(displayio.TileGrid):
    def __init__(self):
        super().__init__(bitmap=bitmap, pixel_shader=displayio.ColorConverter(), width=1, height=4, tile_width=20, tile_height=24)
        self.order = shuffled(range(20))
        self.state = STOPPED
        self.pos = 0

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
        if self.state == BRAKING:
            print (self.pos, yy, off)
        if self.state == BRAKING and self.vel == 7 and yyy < 4:
            self.pos = off * 24 * 16
            self.vel = 0
            yy = 0
            print("braking -> stopped")
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
for i in range(3):
    strip = Strip()
    strip.x = i * 22
    strip.y = -20
    g.append(strip)
    strips.append(strip)
p.show(g)

orders = [shuffled(range(20)), shuffled(range(20)), shuffled(range(20))]

for si, oi in zip(strips, orders):
    for j in range(4):
        si[j] = oi[j]
    
def scroll(t, b):
    sp = b' ' * linelen
    t = sp + t + sp
    b = sp + b + sp
    maxlen = max(len(t), len(b))
    
    for i in range(maxlen-linelen):
        for j in range(linelen):
            sh[j][1] = wheel(3 * (2*i+j))
            tg1[j][0] = charmap[t[i+j]]
            tg2[j][0] = charmap[b[i+j]]
        for j in range(7):
            l1.x = -j
            l2.x = -j
            p.refresh(minimum_frames_per_second=0)
            #p.refresh(minimum_frames_per_second=0)

def all_stopped():
    return all(si.state == STOPPED for si in strips)

for i, si in enumerate(strips):
    si.kick(i)

while True:
    p.refresh(minimum_frames_per_second=0)
    if all_stopped():
        for i, si in enumerate(strips):
            print(si.pos, si.vel, si.y)
        for i in range(100):
            p.refresh(minimum_frames_per_second=0)
        for i, si in enumerate(strips):
            si.kick(i)

    for i, si in enumerate(strips):
        si.step()

