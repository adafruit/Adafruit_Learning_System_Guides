# SPDX-FileCopyrightText: 2026 John Park with Claude Opus 5.5 for Adafruit Industries
#
# SPDX-License-Identifier: MIT
"""Step 2: how fast can Viper push pixels to the 320x240 RGB565 HDMI framebuffer?

Prints one-shot timings, then runs a vblank-locked animation (render to a back
buffer, wait for vblank, copy to the screen) and reports its frame rate.
"""

import array
import gc
import time

import board
import displayio
import microcontroller
import picodvi

import fbtest

WIDTH = 320
HEIGHT = 240
PIXELS = WIDTH * HEIGHT
REPEATS = 20
REPORT_SECONDS = 2

displayio.release_displays()
framebuffer = picodvi.Framebuffer(
    WIDTH,
    HEIGHT,
    clk_dp=board.CKP,
    clk_dn=board.CKN,
    red_dp=board.D0P,
    red_dn=board.D0N,
    green_dp=board.D1P,
    green_dn=board.D1N,
    blue_dp=board.D2P,
    blue_dn=board.D2N,
    color_depth=16,
)
screen = memoryview(framebuffer).cast("B")
# After the framebuffer, about 147 KB of internal SRAM is left: enough for a
# 320x200 RGB565 back buffer (letterboxed) or a 320x240 8-bit one, but not a
# full 320x240 RGB565 one. Anything bigger lands in PSRAM, which takes writes at
# only ~8.5 MB/s.
BACK_HEIGHT = 200
BACK_PIXELS = WIDTH * BACK_HEIGHT
TOP = (HEIGHT - BACK_HEIGHT) // 2 * WIDTH * 2
back = bytearray(BACK_PIXELS * 2)
letterbox = screen[TOP : TOP + BACK_PIXELS * 2]
psram = bytearray(PIXELS * 2)  # past the SRAM, so this one lands in PSRAM
index8 = bytearray(PIXELS)
palette = array.array("H", [((i >> 3) << 11) | (i >> 2) << 5 | (31 - (i >> 3)) for i in range(256)])
wait_for_vblank = getattr(framebuffer, "wait_for_vblank", None)
gc.collect()

args = array.array("i", [0] * fbtest.ARGS_LEN)
args[fbtest.ARG_WIDTH] = WIDTH
args[fbtest.ARG_HEIGHT] = HEIGHT
args[fbtest.ARG_COUNT] = PIXELS
args[fbtest.ARG_COLOR] = 0x07E0

print("cpu %d MHz, free heap %d" % (microcontroller.cpu.frequency // 1000000, gc.mem_free()))
print("screen at 0x%08x, %d bytes" % (fbtest.address(screen), len(screen)))
print("back   at 0x%08x, %d bytes" % (fbtest.address(back), len(back)))
print("psram  at 0x%08x, %d bytes" % (fbtest.address(psram), len(psram)))
print("index8 at 0x%08x, palette at 0x%08x" % (fbtest.address(index8), fbtest.address(palette)))
print("wait_for_vblank:", "yes" if wait_for_vblank else "NO")


def bench(name, func, *buffers):
    start = time.monotonic_ns()
    for _ in range(REPEATS):
        func(*buffers)
    ms = (time.monotonic_ns() - start) / REPEATS / 1e6
    print("%-24s %6.2f ms  %5.1f Mpixel/s" % (name, ms, PIXELS / ms / 1000))


def slice_copy(dest, src):
    dest[:] = src


PAIRS = PIXELS // 2
BACK_PAIRS = BACK_PIXELS // 2
bench("fill16 (naive viper)", fbtest.fill16, screen, args)
bench("fill32_fast -> screen", fbtest.fill32_fast, screen, PAIRS, 0x07E007E0)
bench("fill32_asm -> screen", fbtest.fill32_asm, fbtest.address(screen), PAIRS, 0x07E0)
bench("fill32_asm -> psram", fbtest.fill32_asm, fbtest.address(psram), PAIRS, 0x07E0)
bench("pattern_fast -> screen", fbtest.pattern_fast, screen, PAIRS, args)
bench("pattern_fast -> back200", fbtest.pattern_fast, back, BACK_PAIRS, args)
bench("slice back200 -> screen", slice_copy, letterbox, back)
bench("slice psram -> screen", slice_copy, screen, psram)
bench(
    "expand8 -> screen",
    fbtest.expand8_asm,
    fbtest.address(screen),
    fbtest.address(index8),
    PIXELS,
    fbtest.address(palette),
)

if wait_for_vblank:
    wait_for_vblank()
    start = time.monotonic_ns()
    for _ in range(60):
        wait_for_vblank()
    print("vblank period %.2f ms" % ((time.monotonic_ns() - start) / 60 / 1e6))

print("animating: pattern_fast -> 320x200 back buffer, wait for vblank, copy to screen")
frames = 0
render_ns = 0
copy_ns = 0
report_at = time.monotonic_ns() + REPORT_SECONDS * 1_000_000_000
while True:
    t0 = time.monotonic_ns()
    fbtest.pattern_fast(back, BACK_PAIRS, args)
    t1 = time.monotonic_ns()
    if wait_for_vblank:
        wait_for_vblank()
    t2 = time.monotonic_ns()
    letterbox[:] = back
    t3 = time.monotonic_ns()
    args[fbtest.ARG_TIME] += 1
    frames += 1
    render_ns += t1 - t0
    copy_ns += t3 - t2
    if t3 >= report_at:
        print(
            "%.1f fps | render %.2f ms, copy %.2f ms"
            % (frames / REPORT_SECONDS, render_ns / frames / 1e6, copy_ns / frames / 1e6)
        )
        frames = render_ns = copy_ns = 0
        report_at += REPORT_SECONDS * 1_000_000_000
