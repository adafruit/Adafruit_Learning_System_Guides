"""
RGB Matrix Ocean Scroller
Adafruit invests time and resources providing this open source code.
Please support Adafruit and open source hardware by purchasing
products from Adafruit!
Written by Jeff Epler & Limor Fried for Adafruit Industries
Copyright (c) 2019-2020 Adafruit Industries
Licensed under the MIT license.
All text above must be included in any redistribution.
"""

import math
import time
import random

import adafruit_imageload.bmp
import board
import displayio
import framebufferio
import rgbmatrix
import ulab

displayio.release_displays()

class Reshader:
    '''reshader fades the image to mimic brightness control'''
    def __init__(self, palette):
        self.palette = palette
        ulab_palette = ulab.numpy.zeros((len(palette), 3))
        for i in range(len(palette)):
            rgb = int(palette[i])
            ulab_palette[i, 2] = rgb & 0xff
            ulab_palette[i, 1] = (rgb >> 8) & 0xff
            ulab_palette[i, 0] = rgb >> 16
        self.ulab_palette = ulab_palette

    def reshade(self, brightness):
        '''reshader'''
        palette = self.palette
        shaded = ulab.numpy.array(self.ulab_palette * brightness, dtype=ulab.numpy.uint8)
        for i in range(len(palette)):
            palette[i] = tuple(shaded[i])

def do_crawl_down(image_file, *,
                  speed=12, weave=4, pulse=.5,
                  weave_speed=1/6, pulse_speed=1/7):
    # pylint:disable=too-many-locals
    '''function to scroll the image'''
    the_bitmap, the_palette = adafruit_imageload.load(
        image_file,
        bitmap=displayio.Bitmap,
        palette=displayio.Palette)

    shader = Reshader(the_palette)

    group = displayio.Group()
    tile_grid = displayio.TileGrid(bitmap=the_bitmap, pixel_shader=the_palette)
    group.append(tile_grid)
    display.show(group)

    start_time = time.monotonic_ns()
    start_y = display.height   # High enough to be "off the top"
    end_y = -the_bitmap.height     # Low enough to be "off the bottom"

    # Mix up how the bobs and brightness change on each run
    r1 = random.random() * math.pi
    r2 = random.random() * math.pi

    y = start_y
    while y > end_y:
        now = time.monotonic_ns()
        y = start_y - speed * ((now - start_time) / 1e9)
        group.y = round(y)

        # wave from side to side
        group.x = round(weave * math.cos(y * weave_speed + r1))

        # Change the brightness
        if pulse > 0:
            shader.reshade((1 - pulse) + pulse * math.sin(y * pulse_speed + r2))

        display.refresh(minimum_frames_per_second=0, target_frames_per_second=60)

def do_pulse(image_file, *, duration=4, pulse_speed=1/8, pulse=.5):
    '''pulse animation'''
    the_bitmap, the_palette = adafruit_imageload.load(
        image_file,
        bitmap=displayio.Bitmap,
        palette=displayio.Palette)

    shader = Reshader(the_palette)

    group = displayio.Group()
    tile_grid = displayio.TileGrid(bitmap=the_bitmap, pixel_shader=the_palette)
    group.append(tile_grid)
    group.x = (display.width - the_bitmap.width) // 2
    group.y = (display.height - the_bitmap.height) // 2
    display.show(group)

    start_time = time.monotonic_ns()
    end_time = start_time + int(duration * 1e9)

    now_ns = time.monotonic_ns()
    while now_ns < end_time:
        now_ns = time.monotonic_ns()
        current_time = (now_ns - start_time) / 1e9

        shader.reshade((1 - pulse) - pulse
                       * math.cos(2*math.pi*current_time*pulse_speed)**2)

        display.refresh(minimum_frames_per_second=0, target_frames_per_second=60)

matrix = rgbmatrix.RGBMatrix(
    width=64, height=32, bit_depth=5,
    rgb_pins=[board.D6, board.D5, board.D9, board.D11, board.D10, board.D12],
    addr_pins=[board.A5, board.A4, board.A3, board.A2],
    clock_pin=board.D13, latch_pin=board.D0, output_enable_pin=board.D1)
display = framebufferio.FramebufferDisplay(matrix, auto_refresh=False)

# Image playlist - set to run randomly. Set pulse from 0 to .5
while True:
    show_next = random.randint(1, 5) #change to reflect how many images you add
    if show_next == 1:
        do_crawl_down("/ray.bmp")
    elif show_next == 2:
        do_crawl_down("/waves1.bmp", speed=7, weave=0, pulse=.35)
    elif show_next == 3:
        do_crawl_down("/waves2.bmp", speed=9, weave=0, pulse=.35)
    elif show_next == 4:
        do_pulse("/heart.bmp", duration=4, pulse=.45)
    elif show_next == 5:
        do_crawl_down("/dark.bmp")
