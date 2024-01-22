# SPDX-FileCopyrightText: 2024 Liz Clark for Adafruit Industries
# SPDX-License-Identifier: MIT
# Written by Liz Clark (Adafruit Industries)
# with OpenAI ChatGPT v4 Jan 10, 2024 build
# https://help.openai.com/en/articles/6825453-chatgpt-release-notes

# https://chat.openai.com/share/19de8f24-3191-43b8-a9c9-95f1b8000e80

import time
from math import atan2, degrees, cos, sin, radians
import adafruit_lis3mdl
import vectorio
import displayio
from adafruit_display_text import bitmap_label
from adafruit_bitmap_font import bitmap_font
from adafruit_qualia.graphics import Graphics, Displays
from adafruit_lsm6ds.lsm6dsox import LSM6DSOX
from gamblor21_ahrs import mahony
import bitmaptools
from jpegio import JpegDecoder
# change these values to your calibration values
MAG_MIN = [-11.5902, -47.1353, -28.7635]
MAG_MAX = [79.7866, 48.0854, 63.461]
GYRO_CAL = [-7.3934, -0.000100605, 2.7703]
# use filter for more accurate, but slightly slower readings
# otherwise just reads from magnetometer
ahrs = True
center_x, center_y = 240, 240

graphics = Graphics(Displays.ROUND21, default_bg=None, auto_refresh=False)

i2c = graphics.i2c_bus
accel_gyro = LSM6DSOX(i2c)
magnetometer = adafruit_lis3mdl.LIS3MDL(i2c)
# Create the AHRS filter
ahrs_filter = mahony.Mahony(50, 5, 100)

group = displayio.Group()
# palette for vectorio graphics
pointer_pal = displayio.Palette(5)
pointer_pal[0] = 0xFFFF00
pointer_pal[1] = 0x000000
pointer_pal[2] = 0xFFFFFF
pointer_pal[3] = 0xFF0000
pointer_pal[4] = 0x0000FF
pointer_pal.make_transparent(0)
# compass image is a jpeg
decoder = JpegDecoder()
width, height = decoder.open("/compass.jpg")
bitmap_compass = displayio.Bitmap(width, height, 20)
palette_compass = displayio.ColorConverter(input_colorspace = displayio.Colorspace.RGB565_SWAPPED)
decoder.decode(bitmap_compass)
# blank bitmap for rotozoom
compass_blank = displayio.Bitmap(width, height, 1)
# carrier bitmap for compass for rotozoom
compass_scribble = displayio.Bitmap(width, height, 20)
tile_grid = displayio.TileGrid(compass_scribble, pixel_shader=palette_compass)
# only tilegrid is added to group
group.append(tile_grid)

radius = center_x
angle = 225
rad_angle = radians(angle)

# place small circle to denote heading direction from 9-DoF relative to display
circle_radius = 5
header_angle = radians(135)
edge_x = center_x + radius * cos(header_angle)
edge_y = center_y + radius * sin(header_angle)
adjusted_x = edge_x - circle_radius * cos(header_angle)
adjusted_y = edge_y - circle_radius * sin(header_angle)
header = vectorio.Circle(pixel_shader=pointer_pal, color_index = 2,
                         radius=circle_radius, x=int(adjusted_x), y=int(adjusted_y))

center = vectorio.Circle(pixel_shader=pointer_pal, color_index = 2, radius=50, x=240, y=240)

font_file = "/Roboto-Regular-47.pcf"
font = bitmap_font.load_font(font_file)

direction_text = bitmap_label.Label(font, text="000", color=None)
direction_text.x = center.x - 40
direction_text.y = center.y
direction_bitmap = direction_text.bitmap

direction_blank = displayio.Bitmap(direction_text.bounding_box[2],
                                   direction_text.bounding_box[2], 1)
direction_scribble = displayio.Bitmap(direction_text.bounding_box[2],
                                      direction_text.bounding_box[2], len(pointer_pal))
direction_grid = displayio.TileGrid(direction_scribble, pixel_shader=pointer_pal, x=200, y=200)

def create_line_of_squares(l, n, color):
    squares = []
    square_size = l // n
    for i in range(n):
        x = center_x + i * square_size
        y = center_y - square_size // 2
        square_points = [(0, 0), (square_size, 0),
                        (square_size, square_size), (0, square_size)]
        square = vectorio.Polygon(pixel_shader=pointer_pal,
                                  color_index=color, points=square_points, x=x, y=y)
        group.append(square)
        squares.append(square)
    return squares

def update_line_of_squares(squares, h, l):
    r = radians(-h)
    n = len(squares)
    square_size = l // n
    x = center_x - (square_size - 2)
    y = center_y - (square_size - 2)
    for i, square in enumerate(squares):
        offset_x = x + i * square_size - x
        offset_y = -square_size // 2
        rotated_x = offset_x * cos(r) - offset_y * sin(r)
        rotated_y = offset_x * sin(r) + offset_y * cos(r)
        square.x = int(x + rotated_x)
        square.y = int(y + rotated_y)

length = 200  # Length of the lines
num_squares = 20  # Number of squares for each line

vertical_squares = create_line_of_squares(length, num_squares, 3)
update_line_of_squares(vertical_squares, angle, length)

def map_range(x, in_min, in_max, out_min, out_max):
    mapped = (x - in_min) * (out_max - out_min) / (in_max - in_min) + out_min
    if out_min <= out_max:
        return max(min(mapped, out_max), out_min)

    return min(max(mapped, out_max), out_min)

group.append(center)
group.append(header)
group.append(direction_text)
group.append(direction_grid)

graphics.display.root_group = group

last_heading = angle
heading = angle
last_update = time.monotonic()  # last time we printed the yaw/pitch/roll values
timestamp = time.monotonic_ns()  # used to tune the frequency to approx 100 Hz
spin_rose = True

graphics.display.refresh()

while True:
    if graphics.touch.touched:
        spin_rose = not spin_rose
        # reset last_heading to trigger an update
        last_heading = heading + 5
        if spin_rose:
            direction_text.color = None
            update_line_of_squares(vertical_squares, angle, length)
        else:
            bitmaptools.rotozoom(compass_scribble, bitmap_compass, angle = radians(0))
            direction_text.color = pointer_pal[1]
        graphics.display.refresh()
        # touch debounce delay
        time.sleep(0.2)
    if (time.monotonic_ns() - timestamp) > 6500000:
        mx, my, mz = magnetometer.magnetic
        cal_x = map_range(mx, MAG_MIN[0], MAG_MAX[0], -1, 1)
        cal_y = map_range(my, MAG_MIN[1], MAG_MAX[1], -1, 1)
        cal_z = map_range(mz, MAG_MIN[2], MAG_MAX[2], -1, 1)
        if ahrs:
            ax, ay, az, gx, gy, gz = accel_gyro.acceleration + accel_gyro.gyro
            gx += GYRO_CAL[0]
            gy += GYRO_CAL[1]
            gz += GYRO_CAL[2]
            ahrs_filter.update(gx, gy, -gz, ax, ay, az, cal_x, -cal_y, cal_z)
            yaw_degree = ahrs_filter.yaw
            heading = degrees(yaw_degree)
        else:
            heading = degrees(atan2(cal_y, cal_x))
        timestamp = time.monotonic_ns()
    if time.monotonic() > last_update + 0.2:
        if heading < 0:
            heading += 360
        if abs(last_heading - heading) >= 2:
            direction_text.text = str(int(heading))
            if spin_rose:
                direction_bitmap = direction_text.bitmap

                bitmaptools.rotozoom(compass_scribble, bitmap_compass,
                                     angle = radians(-heading+angle))
                bitmaptools.rotozoom(direction_scribble, direction_bitmap, angle = rad_angle)
                graphics.display.refresh()
                bitmaptools.rotozoom(direction_scribble, direction_blank, angle = rad_angle)
                bitmaptools.rotozoom(compass_scribble, compass_blank,
                                     angle = radians(-heading+angle))
            else:
                update_line_of_squares(vertical_squares, -heading + 90, length)
                graphics.display.refresh()
            last_heading = heading
        last_update = time.monotonic()
