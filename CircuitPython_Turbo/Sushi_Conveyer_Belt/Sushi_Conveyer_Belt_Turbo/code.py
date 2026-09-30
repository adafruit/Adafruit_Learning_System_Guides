# SPDX-FileCopyrightText: 2026 Liz Clark for Adafruit Industries
#
# SPDX-License-Identifier: MIT
"""Sushi conveyor belt on a Qualia S3 with
either 320x820 or 240x960 bar display
graphics code in turbo (lib/sushi_viper.mpy).
"""

import os
import random
import time

import board
import busio
import displayio
import dotclockframebuffer

import sushi_viper
from panels import PANELS

# "bar320x820" (3.2") or "bar240x960" (3.7").
DISPLAY = "bar320x820"
# The TFT's I/O expander address None uses the board default (0x3F).
IO_EXPANDER_ADDRESS = None
# Belt speed. Positive moves the plates right in the landscape art,
# negative left
PIXELS_PER_FRAME = 1
# None runs at the panel's own refresh rate
MAX_FPS = None
ASSET_FOLDER = "/sushi"
# The palette index that is see-through in the plates and the belt slat.
TRANSPARENT_INDEX = 1
# How far the belt's top edge is below the top of the landscape background,
# in pixels.
BELT_TOP = {"bar320x820": 156, "bar240x960": 90}
# Slats repeat every SLAT_PITCH pixels along the belt. None puts them end to
# end at the slat's own width
SLAT_PITCH = None
# Each plate is centered on its slat
PLATE_OFFSET = (0, 0)

displayio.release_displays()
panel = PANELS[DISPLAY]
i2c = busio.I2C(board.SCL, board.SDA, frequency=panel["i2c_frequency"])
io_expander = dict(board.TFT_IO_EXPANDER)
if IO_EXPANDER_ADDRESS is not None:
    io_expander["i2c_address"] = IO_EXPANDER_ADDRESS
dotclockframebuffer.ioexpander_send_init_sequence(
    i2c, panel["init_sequence"], **io_expander
)
i2c.deinit()
framebuffer_settings = dict(board.TFT_PINS)
framebuffer_settings.update(panel["timings"])
framebuffer = dotclockframebuffer.DotClockFramebuffer(**framebuffer_settings)
screen_width, screen_height = framebuffer.width, framebuffer.height
first_pixel = framebuffer.first_pixel_offset // 2
row_stride = framebuffer.row_stride // 2
framebuffer_pixels = len(memoryview(framebuffer))
print(
    f"{DISPLAY}: {screen_width}x{screen_height}, row stride {row_stride} px, "
    f"first pixel {first_pixel}, panel refresh {framebuffer.refresh_rate} Hz"
)

load_start = time.monotonic()
background = sushi_viper.IndexedBMP(
    "%s/sushi_background_%dx%d.bmp" % (ASSET_FOLDER, screen_height, screen_width)
)
if (background.width, background.height) != (screen_height, screen_width):
    raise ValueError(
        "background is %dx%d, needs to be %dx%d"
        % (background.width, background.height, screen_height, screen_width)
    )
background.draw_rotated(framebuffer, first_pixel, row_stride, framebuffer_pixels)
del background

def plate_number(name):
    """The number in sushi_<number>.bmp, or None for any other file."""
    if name.startswith("sushi_") and name.endswith(".bmp") and name[6:-4].isdigit():
        return int(name[6:-4])
    return None

plate_paths = [
    "%s/sushi_%d.bmp" % (ASSET_FOLDER, number)
    for number in sorted(
        plate_number(name)
        for name in os.listdir(ASSET_FOLDER)
        if plate_number(name) is not None
    )
]
tiles, tile_width, tile_height, belt_x = sushi_viper.load_tiles(
    framebuffer,
    first_pixel,
    row_stride,
    screen_width,
    BELT_TOP[DISPLAY],
    ASSET_FOLDER + "/sushi_belt.bmp",
    plate_paths,
    TRANSPARENT_INDEX,
    SLAT_PITCH,
    PLATE_OFFSET,
)
print(
    "%d plates on %dx%d tiles, loaded in %.2f s"
    % (len(plate_paths), tile_width, tile_height, time.monotonic() - load_start)
)

# belt
slots, params, seen = sushi_viper.new(
    screen_width,
    screen_height,
    first_pixel,
    row_stride,
    framebuffer_pixels,
    len(plate_paths),
    tile_width,
    tile_height,
    belt_x,
)
loop_length = sushi_viper.loop_length(params)
sushi_viper.recycle(
    slots, params, seen, len(plate_paths), random.randrange, everything=True
)
print(f"{len(slots)} slots, belt loop {loop_length} px")

frame_ns = 1_000_000_000 // (MAX_FPS or framebuffer.refresh_rate)
next_frame_ns = time.monotonic_ns()
frames = draw_ns = flush_ns = 0
report_ns = next_frame_ns + 2_000_000_000
scroll = 0

while True:
    params[sushi_viper.PARAM_SCROLL] = scroll
    # swap in new plates for slots that have gone off screen
    sushi_viper.recycle(slots, params, seen, len(plate_paths), random.randrange)

    draw_start_ns = time.monotonic_ns()
    sushi_viper.draw_belt(framebuffer, tiles, slots, params)
    draw_end_ns = time.monotonic_ns()
    framebuffer.refresh()
    flush_end_ns = time.monotonic_ns()

    scroll = (scroll + PIXELS_PER_FRAME) % loop_length

    frames += 1
    draw_ns += draw_end_ns - draw_start_ns
    flush_ns += flush_end_ns - draw_end_ns
    if flush_end_ns >= report_ns:
        print(
            "%d fps, draw %d us, refresh %d us"
            % (frames // 2, draw_ns // frames // 1000, flush_ns // frames // 1000)
        )
        frames = draw_ns = flush_ns = 0
        report_ns += 2_000_000_000

    next_frame_ns += frame_ns
    wait_ns = next_frame_ns - time.monotonic_ns()
    if wait_ns > 0:
        time.sleep(wait_ns / 1e9)
    else:
        next_frame_ns = time.monotonic_ns()
