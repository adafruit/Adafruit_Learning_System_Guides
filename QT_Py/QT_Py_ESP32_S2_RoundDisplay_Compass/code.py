# SPDX-FileCopyrightText: 2025 Tim Cocks for Adafruit Industries
# SPDX-License-Identifier: MIT
#
# Adapted from QualiaS3 Compass Learn Guide by Liz Clark (Adafruit Industries)
# https://learn.adafruit.com/qualia-s3-compass/

import time
from math import atan2, degrees, radians
import adafruit_lis3mdl
import board
from adafruit_lsm6ds.lsm6dsox import LSM6DSOX
from gamblor21_ahrs import mahony
import bitmaptools
from adafruit_gc9a01a import GC9A01A
import adafruit_imageload
import displayio
from fourwire import FourWire


# change these values to your calibration values
MAG_MIN = [-75.1973, -22.5665, -34.5221]
MAG_MAX = [-1.2131, 68.1379, 20.8126]
GYRO_CAL = [-0.0038, -0.0026, -0.0011]


# use filter for more accurate, but slightly slower readings
# otherwise just reads from magnetometer
ahrs = True
center_x, center_y = 120, 120

i2c = board.STEMMA_I2C()
accel_gyro = LSM6DSOX(i2c)
magnetometer = adafruit_lis3mdl.LIS3MDL(i2c)
# Create the AHRS filter
ahrs_filter = mahony.Mahony(50, 5, 100)

# Variable to account for the offset between raw heading values
# and the orientation of the display.
offset_angle = 90


def map_range(x, in_min, in_max, out_min, out_max):
    """
    Maps a value from one range to another.

    :param x: The value to map
    :param in_min: The minimum value of the input range
    :param in_max: The maximum value of the input range
    :param out_min: The minimum value of the output range
    :param out_max: The maximum value of the output range

    :return: The value mapped to the output range
    """
    mapped = (x - in_min) * (out_max - out_min) / (in_max - in_min) + out_min
    if out_min <= out_max:
        return max(min(mapped, out_max), out_min)

    return min(max(mapped, out_max), out_min)

last_heading = offset_angle
heading = offset_angle
last_update = time.monotonic()  # last time we printed the yaw/pitch/roll values
timestamp = time.monotonic_ns()  # used to tune the frequency to approx 100 Hz

# Display Setup
spi = board.SPI()
tft_cs = board.TX
tft_dc = board.RX
displayio.release_displays()
display_bus = FourWire(spi, command=tft_dc, chip_select=tft_cs, reset=None)
display = GC9A01A(display_bus, width=240, height=240)
display.rotation = 90

# group to hold all of our visual elements
main_group = displayio.Group()
display.root_group = main_group

# load the compass rose background image
rose_bmp, rose_palette = adafruit_imageload.load("compass_rose.png")
rose_tg = displayio.TileGrid(bitmap=rose_bmp, pixel_shader=rose_palette)

# bitmap for the pointer needle
pointer = displayio.Bitmap(5, 90, 2)

# bitmap for erasing the pointer needle
pointer_eraser = displayio.Bitmap(5, 90, 1)

# pointer needle palette, red foreground, transparent background
pointer_palette = displayio.Palette(2)
pointer_palette[0] = 0x000000
pointer_palette[1] = 0xFF0000
pointer_palette.make_transparent(0)
pointer.fill(1)

# display sized bitmap to paste the rotated needle into
rotated_pointer = displayio.Bitmap(240, 240, 2)

# tilegrid for the rotated pointer needle
pointer_tg = displayio.TileGrid(rotated_pointer, pixel_shader=pointer_palette)

# add rose then pointer to the displaying group
main_group.append(rose_tg)
main_group.append(pointer_tg)

while True:
    # if it's time to take a compass reading from the mag/gyro
    if (time.monotonic_ns() - timestamp) > 6500000:
        # read magnetic data
        mx, my, mz = magnetometer.magnetic

        # map it to the calibrated values
        cal_x = map_range(mx, MAG_MIN[0], MAG_MAX[0], -1, 1)
        cal_y = map_range(my, MAG_MIN[1], MAG_MAX[1], -1, 1)
        cal_z = map_range(mz, MAG_MIN[2], MAG_MAX[2], -1, 1)

        # if using ahrs filter
        if ahrs:
            # get accel/gyro data
            ax, ay, az, gx, gy, gz = accel_gyro.acceleration + accel_gyro.gyro

            # apply callibration offset
            gx += GYRO_CAL[0]
            gy += GYRO_CAL[1]
            gz += GYRO_CAL[2]

            # update filter
            ahrs_filter.update(gx, gy, -gz, ax, ay, az, cal_x, -cal_y, cal_z)

            # get yaw
            yaw_degree = ahrs_filter.yaw

            # convert radians to degrees
            heading = degrees(yaw_degree)

        else:  # not using ahrs filter
            # calculate heading from calibrated mag data
            # and convert from radians to degrees
            heading = degrees(atan2(cal_y, cal_x))

        # save time to compare next iteration
        timestamp = time.monotonic_ns()

    # if it's time to update the display
    if time.monotonic() > last_update + 0.2:
        # wrap negative heading values
        if heading < 0:
            heading += 360

        # if the heading is sufficiently different from previous heading
        if abs(last_heading - heading) >= 2:
            #print(heading)

            # erase the previous pointer needle
            bitmaptools.rotozoom(rotated_pointer, pointer_eraser,
                                 ox=120, oy=120,
                                 px=pointer.width // 2, py=pointer.height,
                                 angle=radians(last_heading + offset_angle))

            # draw the new pointer needle
            bitmaptools.rotozoom(rotated_pointer, pointer,
                                 ox=120, oy=120,
                                 px=pointer.width // 2, py=pointer.height,
                                 angle=radians(heading + offset_angle))

            # set the previous heading to compare next iteration
            last_heading = heading

        # set the last update time to compare next iteration
        last_update = time.monotonic()
