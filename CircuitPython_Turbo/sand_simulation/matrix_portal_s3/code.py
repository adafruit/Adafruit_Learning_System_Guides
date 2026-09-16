# SPDX-FileCopyrightText: 2026 Mikey Sklar for Adafruit Industries
# SPDX-FileCopyrightText: 2020 Phil Burgess for Adafruit Industries
# SPDX-License-Identifier: MIT
#
# "Pixel dust" on a 64x64 HUB75 panel, Matrix Portal S3 edition. Tilt the
# board and the sand runs with gravity, read from the onboard LIS3DH, around
# the Adafruit logo as in PixelDust's demo3-logo. The
# physics lives in src/sand.py so turbo can compile it; this file only wires
# up the display, the accelerometer and the frame loop. Prints frames/second
# and the time spent in the kernel every 100 frames.
import time
from array import array

import adafruit_lis3dh
import board
import displayio
import framebufferio
import rgbmatrix

import logo
import sand

displayio.release_displays()

# 64x64 panel, 1/32 scan, five address lines (MTX_ADDRA..E).
WIDTH, HEIGHT = 64, 64
MAX_FPS = 1000  # the C demo uses 45; 1000 is effectively unthrottled
ELASTICITY = 128  # bounce keeps this /256 of its speed
# Grains start as N_COLORS blocks of BOX_WIDTH x BOX_HEIGHT along the bottom.
N_COLORS = 8
BOX_WIDTH = WIDTH // N_COLORS
BOX_HEIGHT = 8
N_GRAINS = N_COLORS * BOX_WIDTH * BOX_HEIGHT
OBSTACLE = N_COLORS + 1  # cell value for the logo in the collision map
BG = (0, 0, 0)  # background behind the logo (demo3-logo.cpp: 0, 20, 80)
# Which accelerometer axis feeds which simulation axis, and its sign. The
# panel's orientation relative to the LIS3DH is not something the code can
# know; flip these if the sand runs the wrong way.
AX, AY, AZ = (0, 1), (1, 1), (2, 1)

matrix = rgbmatrix.RGBMatrix(
    width=WIDTH,
    height=HEIGHT,
    bit_depth=4,
    # This panel has red and blue swapped, so the B pins drive red. For a
    # panel wired the usual way, list them R, G, B.
    rgb_pins=[
        board.MTX_B1,
        board.MTX_G1,
        board.MTX_R1,
        board.MTX_B2,
        board.MTX_G2,
        board.MTX_R2,
    ],
    addr_pins=[
        board.MTX_ADDRA,
        board.MTX_ADDRB,
        board.MTX_ADDRC,
        board.MTX_ADDRD,
        board.MTX_ADDRE,
    ],
    clock_pin=board.MTX_CLK,
    latch_pin=board.MTX_LAT,
    output_enable_pin=board.MTX_OE,
)
display = framebufferio.FramebufferDisplay(matrix, auto_refresh=False)

# Bottom layer: the white logo alpha-blended onto the background, once. The
# palette index is the logo's gray level, so the blend lives in the palette.
LOGO_X = (WIDTH - logo.WIDTH) // 2
LOGO_Y = (HEIGHT - logo.HEIGHT) // 2
backdrop = displayio.Bitmap(WIDTH, HEIGHT, 256)
backdrop_palette = displayio.Palette(256)
for g in range(256):
    a1 = g + 1
    a2 = 257 - a1
    backdrop_palette[g] = (
        ((255 * a1 + BG[0] * a2) >> 8) << 16
        | ((255 * a1 + BG[1] * a2) >> 8) << 8
        | ((255 * a1 + BG[2] * a2) >> 8)
    )
for y in range(logo.HEIGHT):
    for x in range(logo.WIDTH):
        backdrop[LOGO_X + x, LOGO_Y + y] = logo.GRAY[y * logo.WIDTH + x]

# Top layer: the sand. One byte per cell so the Bitmap's buffer maps
# row-major with no padding (width is a multiple of 4). It doubles as the
# kernel's collision map; any nonzero cell is solid, so the logo's mask goes
# in as OBSTACLE cells, drawn transparent so the backdrop shows through.
bitmap = displayio.Bitmap(WIDTH, HEIGHT, 256)
palette = displayio.Palette(OBSTACLE + 1)
palette[0] = 0x000000
palette.make_transparent(0)
palette[OBSTACLE] = 0x000000
palette.make_transparent(OBSTACLE)
for y in range(logo.HEIGHT):
    for x in range(logo.WIDTH):
        if logo.MASK[y * 5 + (x >> 3)] & (0x80 >> (x & 7)):
            bitmap[LOGO_X + x, LOGO_Y + y] = OBSTACLE
for i, rgb in enumerate(
    (
        (64, 64, 64),  # dark gray
        (120, 79, 23),  # brown
        (228, 3, 3),  # red
        (255, 140, 0),  # orange
        (255, 237, 0),  # yellow
        (0, 128, 38),  # green
        (0, 77, 255),  # blue
        (117, 7, 135),  # purple
    )
):
    palette[i + 1] = (rgb[0] << 16) | (rgb[1] << 8) | rgb[2]
group = displayio.Group()
group.append(displayio.TileGrid(backdrop, pixel_shader=backdrop_palette))
group.append(displayio.TileGrid(bitmap, pixel_shader=palette))
display.root_group = group

accel = adafruit_lis3dh.LIS3DH_I2C(board.I2C(), address=0x19)
accel.range = adafruit_lis3dh.RANGE_4_G

grains = array("i", [0] * (5 * N_GRAINS))
rng = array("I", [time.monotonic_ns() & 0x7FFFFFFF])
n = 0
for c in range(N_COLORS):
    for y in range(HEIGHT - BOX_HEIGHT, HEIGHT):
        for x in range(c * BOX_WIDTH, (c + 1) * BOX_WIDTH):
            sand.place(grains, bitmap, n, x, y, WIDTH, c + 1)
            n += 1
bitmap.dirty()
display.refresh()

print(N_GRAINS, "grains")

FRAME_NS = 1_000_000_000 // MAX_FPS
next_frame = time.monotonic_ns()
frames = 0
kernel_ns = 0
t_report = next_frame

while True:
    # Throttle to MAX_FPS. The kernel's time varies with how much is
    # moving, so without this gravity would look stronger in a settled pile.
    now = time.monotonic_ns()
    if now < next_frame:
        continue
    next_frame = now + FRAME_NS

    a = accel.acceleration  # m/s^2
    ax = int(a[AX[0]] * 1000) * AX[1]
    ay = int(a[AY[0]] * 1000) * AY[1]
    az = int(a[AZ[0]] * 1000) * AZ[1]

    t0 = time.monotonic_ns()
    sand.iterate(grains, bitmap, N_GRAINS, WIDTH, HEIGHT, ax, ay, az, ELASTICITY, rng)
    kernel_ns += time.monotonic_ns() - t0
    bitmap.dirty()  # the kernel wrote through the buffer, tell displayio
    display.refresh()

    frames += 1
    if frames == 100:
        elapsed = now - t_report
        print(
            "%.1f fps, kernel %.2f ms/frame, accel (%d, %d, %d)"
            % (frames * 1e9 / elapsed, kernel_ns / frames / 1e6, ax, ay, az)
        )
        frames = 0
        kernel_ns = 0
        t_report = now
