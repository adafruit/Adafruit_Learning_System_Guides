# SPDX-FileCopyrightText: 2023 Liz Clark for Adafruit Industries
# SPDX-FileCopyrightText: Adapted from Phil B.'s 16bit_hello Arduino Code
#
# SPDX-License-Identifier: MIT

import gc
import math
from random import randint
import time
import displayio
import picodvi
import board
import framebufferio
import vectorio
import terminalio
import simpleio
from adafruit_bitmap_font import bitmap_font
from adafruit_display_text import label, wrap_text_to_lines
from adafruit_display_shapes.rect import Rect
from adafruit_display_shapes.circle import Circle
from adafruit_display_shapes.roundrect import RoundRect
from adafruit_display_shapes.triangle import Triangle
from adafruit_display_shapes.line import Line

displayio.release_displays()

# check for DVI Feather
if 'CKP' in dir(board):
    fb = picodvi.Framebuffer(320, 240,
        clk_dp=board.CKP, clk_dn=board.CKN,
        red_dp=board.D0P, red_dn=board.D0N,
        green_dp=board.D1P, green_dn=board.D1N,
        blue_dp=board.D2P, blue_dn=board.D2N,
        color_depth=8)
# otherwise assume Pico
else:
    fb = picodvi.Framebuffer(320, 240,
        clk_dp=board.GP12, clk_dn=board.GP13,
        red_dp=board.GP10, red_dn=board.GP11,
        green_dp=board.GP8, green_dn=board.GP9,
        blue_dp=board.GP6, blue_dn=board.GP7,
        color_depth=8)
display = framebufferio.FramebufferDisplay(fb)

bitmap = displayio.Bitmap(display.width, display.height, 3)

red = 0xff0000
yellow = 0xcccc00
orange = 0xff5500
blue = 0x0000ff
pink = 0xff00ff
purple = 0x5500ff
white = 0xffffff
green =  0x00ff00
aqua = 0x125690

palette = displayio.Palette(3)
palette[0] = 0x000000 # black
palette[1] = white
palette[2] = yellow

palette.make_transparent(0)

tile_grid = displayio.TileGrid(bitmap, pixel_shader=palette)

group = displayio.Group()

def clean_up(group_name):
    for _ in range(len(group_name)):
        group_name.pop()
    gc.collect()

def show_shapes():
    gc.collect()
    cx = int(display.width / 2)
    cy = int(display.height / 2)
    minor = min(cx, cy)
    pad = 5
    size = minor - pad
    half = int(size / 2)
    rect = Rect(cx - minor, cy - minor, size, size, stroke = 1, fill=red, outline = red)
    tri = Triangle(cx + pad, cy - pad, cx + pad + half, cy - minor,
                   cx + minor - 1, cy - pad, fill=green, outline = green)
    circ = Circle(cx - pad - half, cy + pad + half, half, fill=blue, stroke = 1, outline = blue)
    rnd = RoundRect(cx + pad, cy + pad, size, size, int(size / 5), stroke = 1,
                    fill=yellow, outline = yellow)

    group.append(rect)
    group.append(tri)
    group.append(circ)
    group.append(rnd)
    rect.fill = None
    tri.fill = None
    circ.fill = None
    rnd.fill = None

    time.sleep(2)

    rect.fill = red
    tri.fill = green
    circ.fill = blue
    rnd.fill = yellow
    time.sleep(2)
    clean_up(group)
    del rect
    del tri
    del circ
    del rnd
    gc.collect()

def sine_chart():
    gc.collect()
    cx = int(display.width / 2)
    cy = int(display.height / 2)
    minor = min(cx, cy)
    major = max(cx, cy)

    group.append(Line(cx, 0, cx, display.height, blue)) # v
    group.append(Line(0, cy, display.width, cy, blue)) # h

    for i in range(10):
        _n = simpleio.map_range(i, 0, 10, 0, major - 1)
        n = int(_n)
        group.append(Line(cx - n, cy - 5, cx - n, (cy - 5) + 11, blue)) # v
        group.append(Line(cx + n, cy - 5, cx + n, (cy - 5) + 11, blue)) # v
        group.append(Line(cx - 5, cy - n, (cx - 5) + 11, cy - n, blue)) # h
        group.append(Line(cx - 5, cy + n, (cx - 5) + 11, cy + n, blue)) # h

    for x in range(display.width):
        y = cy - int(math.sin((x - cx) * 0.05) * float(minor * 0.5))
        bitmap[x, y] = 1
    group.append(tile_grid)
    time.sleep(2)
    clean_up(group)

def widget0():
    gc.collect()
    data = [31, 42, 36, 58, 67, 88]
    num_points = len(data)

    text_area = label.Label(terminalio.FONT, text="Widget Sales", color=white)
    text_area.anchor_point = (0.5, 0.0)
    text_area.anchored_position = (display.width / 2, 3)
    group.append(text_area)
    for i in range(11):
        _x = simpleio.map_range(i, 0, 10, 0, display.width - 1)
        x = int(_x)
        group.append(Line(x, 20, x, display.height, blue))
        _y = simpleio.map_range(i, 0, 10, 20, display.height - 1)
        y = int(_y)
        group.append(Line(0, y, display.width, y, blue))
    prev_x = 0
    _prev_y = simpleio.map_range(data[0], 0, 100, display.height - 1, 20)
    prev_y = int(_prev_y)
    for i in range(1, num_points):
        _new_x = simpleio.map_range(i, 0, num_points - 1, 0, display.width - 1)
        new_x = int(_new_x)
        _new_y = simpleio.map_range(data[i], 0, 100, display.height - 1, 20)
        new_y = int(_new_y)
        group.append(Line(prev_x, prev_y, new_x, new_y, aqua))
        prev_x = new_x
        prev_y = new_y

    for i in range(num_points):
        _x = simpleio.map_range(i, 0, num_points - 1, 0, display.width - 1)
        x = int(_x)
        _y = simpleio.map_range(data[i], 0, 100, display.height - 1, 20)
        y = int(_y)
        group.append(Circle(x, y, 5, fill=None, stroke = 2, outline = white))

    time.sleep(2)
    clean_up(group)

def widget1():
    gc.collect()
    data = [31, 42, 36, 58, 67, 88]
    num_points = len(data)
    bar_width = int(display.width / num_points) - 4
    x_mapped_w = display.width + 2
    h_mapped_h = display.height + 20

    text_area = label.Label(terminalio.FONT, text="Widget Sales", color=white)
    text_area.anchor_point = (0.5, 0.0)
    text_area.anchored_position = (display.width / 2, 3)
    group.append(text_area)
    for i in range(11):
        _y = simpleio.map_range(i, 0, 10, 20, display.height - 1)
        y = int(_y)
        group.append(Line(0, y, display.width, y, blue))
    for i in range(num_points):
        _x = simpleio.map_range(i, 0, num_points, 0, x_mapped_w)
        x = int(_x)
        _height = simpleio.map_range(data[i], 0, 100, h_mapped_h, 0)
        height = int(_height)
        group.append(vectorio.Rectangle(pixel_shader=palette, width=bar_width,
                     height=display.height + 1, x=x, y=height, color_index = 2))

    time.sleep(2)
    clean_up(group)

def text_align():
    gc.collect()
    TEXT = "hello world"

    text_area_top_left = label.Label(terminalio.FONT, text=TEXT, color=red)
    text_area_top_left.anchor_point = (0.0, 0.0)
    text_area_top_left.anchored_position = (0, 0)

    text_area_top_middle = label.Label(terminalio.FONT, text=TEXT, color=orange)
    text_area_top_middle.anchor_point = (0.5, 0.0)
    text_area_top_middle.anchored_position = (display.width / 2, 0)

    text_area_top_right = label.Label(terminalio.FONT, text=TEXT, color=yellow)
    text_area_top_right.anchor_point = (1.0, 0.0)
    text_area_top_right.anchored_position = (display.width, 0)

    text_area_middle_left = label.Label(terminalio.FONT, text=TEXT, color=green)
    text_area_middle_left.anchor_point = (0.0, 0.5)
    text_area_middle_left.anchored_position = (0, display.height / 2)

    text_area_middle_middle = label.Label(terminalio.FONT, text=TEXT, color=aqua)
    text_area_middle_middle.anchor_point = (0.5, 0.5)
    text_area_middle_middle.anchored_position = (display.width / 2, display.height / 2)

    text_area_middle_right = label.Label(terminalio.FONT, text=TEXT, color=blue)
    text_area_middle_right.anchor_point = (1.0, 0.5)
    text_area_middle_right.anchored_position = (display.width, display.height / 2)

    text_area_bottom_left = label.Label(terminalio.FONT, text=TEXT, color=purple)
    text_area_bottom_left.anchor_point = (0.0, 1.0)
    text_area_bottom_left.anchored_position = (0, display.height)

    text_area_bottom_middle = label.Label(terminalio.FONT, text=TEXT, color=pink)
    text_area_bottom_middle.anchor_point = (0.5, 1.0)
    text_area_bottom_middle.anchored_position = (display.width / 2, display.height)

    text_area_bottom_right = label.Label(terminalio.FONT, text=TEXT, color=white)
    text_area_bottom_right.anchor_point = (1.0, 1.0)
    text_area_bottom_right.anchored_position = (display.width, display.height)

    group.append(text_area_top_middle)
    group.append(text_area_top_left)
    group.append(text_area_top_right)
    group.append(text_area_middle_middle)
    group.append(text_area_middle_left)
    group.append(text_area_middle_right)
    group.append(text_area_bottom_middle)
    group.append(text_area_bottom_left)
    group.append(text_area_bottom_right)

    time.sleep(2)
    clean_up(group)

def custom_font():
    gc.collect()
    my_font = bitmap_font.load_font("/Helvetica-Bold-16.pcf")
    text_sample = "The quick brown fox jumps over the lazy dog."
    text_sample = "\n".join(wrap_text_to_lines(text_sample, 28))
    text_area = label.Label(my_font, text="Custom Font", color=white)
    text_area.anchor_point = (0.0, 0.0)
    text_area.anchored_position = (0, 0)

    sample_text = label.Label(my_font, text=text_sample)
    sample_text.anchor_point = (0.5, 0.5)
    sample_text.anchored_position = (display.width / 2, display.height / 2)

    group.append(text_area)
    group.append(sample_text)

    time.sleep(2)
    clean_up(group)

    del my_font
    gc.collect()

def bitmap_example():
    gc.collect()
    blinka_bitmap = displayio.OnDiskBitmap("/blinka_computer.bmp")
    blinka_grid = displayio.TileGrid(blinka_bitmap, pixel_shader=blinka_bitmap.pixel_shader)
    gc.collect()
    group.append(blinka_grid)

    time.sleep(2)
    clean_up(group)

    del blinka_grid
    del blinka_bitmap
    gc.collect()

def sensor_values():
    gc.collect()
    text_x = "X: %d" % randint(-25, 25)
    text_y = "Y: %d" % randint(-25, 25)
    text_z = "Z: %d" % randint(-25, 25)
    x_text = label.Label(terminalio.FONT, text=text_x, color=red)
    x_text.anchor_point = (0.0, 0.0)
    x_text.anchored_position = (2, 0)
    y_text = label.Label(terminalio.FONT, text=text_y, color=green)
    y_text.anchor_point = (0.0, 0.0)
    y_text.anchored_position = (2, 10)
    z_text = label.Label(terminalio.FONT, text=text_z, color=blue)
    z_text.anchor_point = (0.0, 0.0)
    z_text.anchored_position = (2, 20)
    group.append(x_text)
    group.append(y_text)
    group.append(z_text)

    for i in range(40):
        if i == 10:
            group.scale = 2
        elif i == 20:
            group.scale = 3
        elif i == 30:
            group.scale = 4
        x_text.text = "X: %d" % randint(-50, 50)
        y_text.text = "Y: %d" % randint(-50, 50)
        z_text.text = "Z: %d" % randint(-50, 50)
        time.sleep(0.1)
    time.sleep(0.1)
    clean_up(group)
    group.scale = 1

display.show(group)

while True:
    show_shapes()
    sine_chart()
    widget0()
    widget1()
    text_align()
    custom_font()
    bitmap_example()
    sensor_values()
