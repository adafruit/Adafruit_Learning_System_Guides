# SPDX-FileCopyrightText: 2026 Tim Cocks for Adafruit Industries
#
# SPDX-License-Identifier: MIT
"""Accelerometer sand on a picogame Scene, physics in viper (lib/sand_viper.mpy).
"""

import gc
import math
import random
import time

import board
import displayio
import fourwire
import picogame
import adafruit_ili9341

import sand_viper
import logo

# Grain size: each grain is SCALE x SCALE pixels. The grid is the screen
# divided by SCALE (320x240 at 3 -> 106x80 cells, centered), and the grain
# count is FILL of that, so larger grains also mean fewer of them.
SCALE = 3
FILL = 0.15  # fraction of cells holding a grain
# Grains start as this many horizontal rainbow bands, red at the top through
# blue to magenta at the bottom. 0 scatters the rainbow colors at random.
STRIPES = 6
# Top speed in cells per frame; 1 G tilt adds 1/8 cell per frame each frame,
# so grains accelerate for 8 frames per cell of top speed. Faster grains move
# in one-cell substeps, so they can't jump over one another.
MAX_SPEED = 5
MAX_FPS = 45
SPI_HZ = 75000000
BACKGROUND_RGB = (0, 0, 0)
BACKGROUND_COLOR = picogame.rgb565(*BACKGROUND_RGB)
# The logo is one cell per logo pixel (40x40 cells, 120x120 pixels at SCALE 3),
# drawn in LOGO_RGB blended over BACKGROUND_RGB by the logo's coverage. Grains
# can't enter its solid part, but can cover its faint antialiased edge.
LOGO_RGB = (255, 255, 255)

# The accelerometer's reading, in m/s^2, while resting in the position
# that should count as flat. Every reading is turned by the smallest rotation
# that takes this one to straight along the sensor's z axis, so the sensor can
# be mounted at any angle. (0, 0, 9.8) is a sensor mounted flat. None measures
# it at startup instead (power up with the rig level) and prints the value to
# paste here.
LEVEL = (-9.25, -0.33, -1.32)

# Screen x and y from the leveled accelerometer axes, as (axis index, sign).
# LED_Sand.ino's mapping, (1, -1) and (0, 1), sent the sand uphill with this
# mounting, so both signs are negated; checked by tilting the rig in every
# direction. For a different mounting, negate an axis that runs the wrong way,
# and swap the axis indexes if left/right tilts move the sand up/down.
SCREEN_X = (1, 1)
SCREEN_Y = (0, -1)

displayio.release_displays()
spi_bus = fourwire.FourWire(
    board.SPI(), command=board.D9, chip_select=board.D10, baudrate=SPI_HZ
)
display = adafruit_ili9341.ILI9341(spi_bus, width=320, height=240)
display.auto_refresh = False
use_dma = False
target = (
    picogame.Display(display)
    if use_dma and picogame.FAST_DISPLAY_SUPPORTED
    else display
)
print("picogame backend:", "DMA Display" if target is not display else "BusDisplay")
strip_bytes = display.width * picogame.STRIP_H * 2  # 2 bytes per RGB565 pixel
scene = picogame.Scene(
    target, bytearray(strip_bytes), bytearray(strip_bytes), background=BACKGROUND_COLOR
)
screen_width, screen_height = display.width, display.height

# -- sand -----------------------------------------------------------------

GRID_WIDTH, GRID_HEIGHT = screen_width // SCALE, screen_height // SCALE
GRAIN_COUNT = int(GRID_WIDTH * GRID_HEIGHT * FILL)


gc.collect()
# The four buffers the viper kernels work on; sand_viper.py describes each.
# grains holds 5 ints per grain: x, y, velocity x, velocity y, color. params
# holds the settings, indexed by the sand_viper.PARAM_* constants.
grains, grid, pixels, params = sand_viper.new(
    GRID_WIDTH,
    GRID_HEIGHT,
    GRAIN_COUNT,
    SCALE,
    BACKGROUND_COLOR,
    seed=random.getrandbits(30),
    backdrop_cells=logo.WIDTH * logo.HEIGHT,
)
params[sand_viper.PARAM_MAX_SPEED] = int(MAX_SPEED * 256)  # 256 grain units per cell


# Alpha-blend the logo over the background.
# step() repaints a cell the logo covers with its color
# from params when a grain leaves it.
def blend(coverage):
    """LOGO_RGB over BACKGROUND_RGB, by coverage from 0 (none) to 255 (solid)."""
    logo_weight = coverage + 1
    background_weight = 257 - logo_weight
    return picogame.rgb565(
        *(
            (logo_channel * logo_weight + background_channel * background_weight) >> 8
            for logo_channel, background_channel in zip(LOGO_RGB, BACKGROUND_RGB)
        )
    )


logo_width, logo_height = logo.WIDTH, logo.HEIGHT
mask_row_bytes = (
    logo_width + 7
) // 8  # the mask packs 8 cells per byte, leftmost in the top bit
sand_viper.backdrop(
    grid,
    params,
    (GRID_WIDTH - logo_width) // 2,
    (GRID_HEIGHT - logo_height) // 2,
    logo_width,
    logo_height,
    [blend(coverage) for coverage in logo.GRAY],
    bytes(
        logo.MASK[y * mask_row_bytes + x // 8] & (0x80 >> (x & 7))
        for y in range(logo_height)
        for x in range(logo_width)
    ),
)


def rainbow(hue):
    """Fully saturated color at hue in [0, 1): red, yellow, green, cyan, blue, magenta."""
    scaled_hue = hue * 6
    sector = int(scaled_hue)  # which sixth of the color wheel
    rising = int((scaled_hue - sector) * 255)  # how far through that sixth, 0 to 255
    falling = 255 - rising
    red, green, blue = (
        (255, rising, 0),
        (falling, 255, 0),
        (0, 255, rising),
        (0, falling, 255),
        (rising, 0, 255),
        (255, 0, falling),
    )[sector % 6]
    return picogame.rgb565(red, green, blue)


canvas = scene.add(
    picogame.Canvas(GRID_WIDTH * SCALE, GRID_HEIGHT * SCALE, buffer=pixels)
)
canvas.move(
    (screen_width - GRID_WIDTH * SCALE) // 2, (screen_height - GRID_HEIGHT * SCALE) // 2
)

if STRIPES:
    # A grain's row is only known once place() has scattered it, and place()
    # paints with the colors already in grains. So place once for positions,
    # color by row, then restore the random state and place again to paint.
    saved_random_state = params[sand_viper.PARAM_RANDOM_STATE]
    sand_viper.place(grains, grid, pixels, params)
    for grain in range(GRAIN_COUNT):
        cell_y = grains[5 * grain + 1] >> 8  # grain units to cells: divide by 256
        stripe = cell_y * STRIPES // GRID_HEIGHT
        grains[5 * grain + 4] = rainbow(stripe / max(STRIPES - 1, 1) * 5 / 6)
    params[sand_viper.PARAM_RANDOM_STATE] = saved_random_state
else:
    # place() scatters grains over random cells, so spreading the hues over
    # the grain indices spreads the whole rainbow evenly across the sand.
    for grain in range(GRAIN_COUNT):
        grains[5 * grain + 4] = rainbow(grain / GRAIN_COUNT)
sand_viper.place(grains, grid, pixels, params)

# -- accelerometer --------------------------------------------------------


def make_accelerometer():
    i2c = board.STEMMA_I2C()
    try:
        import adafruit_mpu6050  # pylint: disable=import-outside-toplevel

        mpu6050 = adafruit_mpu6050.MPU6050(i2c)
        mpu6050.accelerometer_range = adafruit_mpu6050.Range.RANGE_4_G
        print("using MPU6050")
        return mpu6050
    except Exception as error:
        print("no MPU6050:", error)
    try:
        import adafruit_lis3dh  # pylint: disable=import-outside-toplevel

        lis3dh = adafruit_lis3dh.LIS3DH_I2C(i2c, address=0x18)
        lis3dh.range = adafruit_lis3dh.RANGE_4_G
        print("using LIS3DH")
        return lis3dh
    except Exception as error:
        print("no LIS3DH:", error)
    print("no accelerometer, simulating one")
    return None


accelerometer = make_accelerometer()
GRAVITY = 9.80665  # 1 G in m/s^2


def level_rotation(rest_reading):
    """Rows of the smallest rotation that takes rest_reading to straight
    along the sensor's z axis, +z or -z, whichever is nearer."""
    rest_x, rest_y, rest_z = rest_reading
    length = math.sqrt(rest_x * rest_x + rest_y * rest_y + rest_z * rest_z)
    unit_x, unit_y, unit_z = rest_x / length, rest_y / length, rest_z / length
    target_z = 1.0 if unit_z >= 0 else -1.0
    # Rodrigues' rotation formula, turning the unit vector u to t = (0, 0,
    # target_z): with v = u x t (the axis to turn about, as long as the sine
    # of the angle; its z is 0) and c = u . t >= 0 (the cosine),
    # R = I + [v]x + [v]x^2 / (1 + c).
    axis_x, axis_y = unit_y * target_z, -unit_x * target_z
    factor = 1 / (1 + unit_z * target_z)
    return (
        (1 - axis_y * axis_y * factor, axis_x * axis_y * factor, axis_y),
        (axis_x * axis_y * factor, 1 - axis_x * axis_x * factor, -axis_x),
        (-axis_y, axis_x, 1 - (axis_x * axis_x + axis_y * axis_y) * factor),
    )


if accelerometer:
    if LEVEL is None:
        totals = [0.0, 0.0, 0.0]
        for _ in range(64):
            reading = accelerometer.acceleration
            totals[0] += reading[0]
            totals[1] += reading[1]
            totals[2] += reading[2]
            time.sleep(0.002)
        LEVEL = (totals[0] / 64, totals[1] / 64, totals[2] / 64)
        print("measured LEVEL = (%.2f, %.2f, %.2f)" % LEVEL)
    # Each row, dotted with a raw reading, gives one leveled axis.
    rotation_x_row, rotation_y_row, rotation_z_row = level_rotation(LEVEL)
    raw_x, raw_y, raw_z = accelerometer.acceleration
    print(
        "leveled reading now (%.2f, %.2f, %.2f) G"
        % tuple(
            (row[0] * raw_x + row[1] * raw_y + row[2] * raw_z) / GRAVITY
            for row in (rotation_x_row, rotation_y_row, rotation_z_row)
        )
    )


def read_acceleration():
    """Return (accel_x, accel_y, jitter_range) in grain units per frame."""
    if accelerometer:
        _raw_x, _raw_y, _raw_z = accelerometer.acceleration
        leveled = (
            rotation_x_row[0] * _raw_x
            + rotation_x_row[1] * _raw_y
            + rotation_x_row[2] * _raw_z,
            rotation_y_row[0] * _raw_x
            + rotation_y_row[1] * _raw_y
            + rotation_y_row[2] * _raw_z,
            rotation_z_row[0] * _raw_x
            + rotation_z_row[1] * _raw_y
            + rotation_z_row[2] * _raw_z,
        )
    else:
        angle = time.monotonic() * 0.4  # simulated gravity turns 0.4 radians per second
        leveled = (
            0.9 * GRAVITY * math.cos(angle),
            -0.9 * GRAVITY * math.sin(angle),
            0.45 * GRAVITY,
        )
    # The original divides raw 4 G-range counts by 256, so 1 G is 32 units.
    _accel_x = int(leveled[SCREEN_X[0]] * SCREEN_X[1] * 32 / GRAVITY)
    _accel_y = int(leveled[SCREEN_Y[0]] * SCREEN_Y[1] * 32 / GRAVITY)
    # Held flat (|z| near 1 G) there is little jitter; tilted up, more.
    flatness = int(abs(leveled[2]) * 4 / GRAVITY)
    jitter = 1 if flatness >= 3 else 4 - flatness
    # step() adds 0 .. 2 * jitter to each axis; subtracting jitter here
    # centers that on zero.
    return _accel_x - jitter, _accel_y - jitter, 2 * jitter + 1


# -- main loop ------------------------------------------------------------

print(
    f"{screen_width}x{screen_height}, {GRAIN_COUNT} grains on {GRID_WIDTH}x{GRID_HEIGHT} cells"
)
frame_ns = 1000000000 // MAX_FPS
next_frame_ns = time.monotonic_ns()
# Totals since the last report, which is every 2 s.
frames = step_ns = draw_ns = pixels_sent = 0
report_ns = next_frame_ns + 2000000000

while True:
    accel_x, accel_y, jitter_range = read_acceleration()
    params[sand_viper.PARAM_ACCEL_X] = accel_x
    params[sand_viper.PARAM_ACCEL_Y] = accel_y
    params[sand_viper.PARAM_JITTER_RANGE] = jitter_range

    step_start_ns = time.monotonic_ns()
    if sand_viper.step(grains, grid, pixels, params):
        # step() wrote pixels straight into the canvas buffer. Rewriting the
        # dirty rectangle's two corner pixels with their own colors makes the
        # canvas mark exactly that rectangle for the next refresh.
        canvas.pixel(
            params[sand_viper.PARAM_DIRTY_LEFT] * SCALE,
            params[sand_viper.PARAM_DIRTY_TOP] * SCALE,
            params[sand_viper.PARAM_TOP_LEFT_COLOR],
        )
        canvas.pixel(
            params[sand_viper.PARAM_DIRTY_RIGHT] * SCALE - 1,
            params[sand_viper.PARAM_DIRTY_BOTTOM] * SCALE - 1,
            params[sand_viper.PARAM_BOTTOM_RIGHT_COLOR],
        )
    step_end_ns = time.monotonic_ns()
    sent_rect = (
        scene.refresh()
    )  # (left, top, right, bottom) sent to the screen, if anything
    draw_end_ns = time.monotonic_ns()
    if sent_rect:
        pixels_sent += (sent_rect[2] - sent_rect[0]) * (sent_rect[3] - sent_rect[1])

    frames += 1
    step_ns += step_end_ns - step_start_ns
    draw_ns += draw_end_ns - step_end_ns
    if draw_end_ns >= report_ns:
        print(
            "%d fps, step %d us, draw %d us, %d px sent/frame"
            % (
                frames // 2,
                step_ns // frames // 1000,
                draw_ns // frames // 1000,
                pixels_sent // frames,
            )
        )
        frames = step_ns = draw_ns = pixels_sent = 0
        report_ns += 2000000000

    next_frame_ns += frame_ns
    wait_ns = next_frame_ns - time.monotonic_ns()
    if wait_ns > 0:
        time.sleep(wait_ns / 1e9)
    else:
        next_frame_ns = time.monotonic_ns()  # running behind: don't try to catch up
