# SPDX-FileCopyrightText: 2024 Liz Clark for Adafruit Industries
# SPDX-License-Identifier: MIT
#
# Adapted from Gamblor21's calibrate.py in the Gamblor21_CircuitPython_AHRS library
# https://github.com/gamblor21/Gamblor21_CircuitPython_AHRS/blob/master/examples/calibrate.py
#
# Gyro will be calibrated first, followed by magnetometer
# Keep the board still for gyro, move around for magnetometer

import time
from adafruit_lsm6ds.lsm6dsox import LSM6DSOX
import adafruit_lis3mdl
from adafruit_qualia.graphics import Graphics, Displays

graphics = Graphics(Displays.ROUND21, default_bg=None, auto_refresh=True)
i2c = graphics.i2c_bus
accel_gyro = LSM6DSOX(i2c)
magnetometer = adafruit_lis3mdl.LIS3MDL(i2c)
MAG_MIN = [1000, 1000, 1000]
MAG_MAX = [-1000, -1000, -1000]

def map_range(x, in_min, in_max, out_min, out_max):
    """
    Maps a number from one range to another.
    :return: Returns value mapped to new range
    :rtype: float
    """
    mapped = (x - in_min) * (out_max - out_min) / (in_max - in_min) + out_min
    if out_min <= out_max:
        return max(min(mapped, out_max), out_min)

    return min(max(mapped, out_max), out_min)

def calibrate_gyro():
    """
    Calibrates gyroscope
    Gyroscope values are in rads/s
    """
    gx, gy, gz = accel_gyro.gyro
    min_gx = gx
    min_gy = gy
    min_gz = gz

    max_gx = gx
    max_gy = gy
    max_gz = gz

    mid_gx = gx
    mid_gy = gy
    mid_gz = gz

    for _ in range(10):
        gx, gy, gz = accel_gyro.gyro

        min_gx = min(min_gx, gx)
        min_gy = min(min_gy, gy)
        min_gz = min(min_gz, gz)

        max_gx = max(max_gx, gx)
        max_gy = max(max_gy, gy)
        max_gz = max(max_gz, gz)

        mid_gx = (max_gx + min_gx) / 2
        mid_gy = (max_gy + min_gy) / 2
        mid_gz = (max_gz + min_gz) / 2

        print("Uncalibrated gyro: ", (gx, gy, gz))
        print("Calibrated gyro: ", (gx + mid_gx, gy + mid_gy, gz + mid_gz))
        print("Gyro calibration: ", (mid_gx, mid_gy, mid_gz))

        time.sleep(1)
    mid_gx = float(f"{mid_gx:.4f}")
    mid_gy = float(f"{mid_gy:.4f}")
    mid_gz = float(f"{mid_gz:.4f}")
    _CAL = [mid_gx, mid_gy, mid_gz]
    return _CAL

def calibrate_mag():
    """
    Calibrates a magnometer
    """
    countavg = 0
    x, y, z = magnetometer.magnetic
    mag_vals = [x, y, z]
    for i in range(3):
        MAG_MIN[i] = min(MAG_MIN[i], mag_vals[i])
        MAG_MAX[i] = max(MAG_MAX[i], mag_vals[i])

    for _ in range(10):
        x, y, z = magnetometer.magnetic
        mag_vals = [x, y, z]

        for i in range(3):
            MAG_MIN[i] = min(MAG_MIN[i], mag_vals[i])
            MAG_MAX[i] = max(MAG_MAX[i], mag_vals[i])

        countavg += 1
        print("Uncalibrated:", x, y, z)
        cal_x = map_range(x, MAG_MIN[0], MAG_MAX[0], -1, 1)
        cal_y = map_range(y, MAG_MIN[1], MAG_MAX[1], -1, 1)
        cal_z = map_range(z, MAG_MIN[2], MAG_MAX[2], -1, 1)
        print("Calibrated:  ", cal_x, cal_y, cal_z)
        print("MAG_MIN =", MAG_MIN)
        print("MAG_MAX =", MAG_MAX)

        time.sleep(1)
    return MAG_MIN, MAG_MAX

print("Preparing gyroscope calibration. Keep board perfectly still on flat surface.")
time.sleep(5)
print("Starting gyroscope calibration..")
print()
GYRO_CAL = calibrate_gyro()
print("Gyroscope calibrated!")

print("Preparing magnetometer calibration. Move board around in 3D space.")
time.sleep(5)
print("Starting magnetometer calibration..")
print()
MAG_MIN, MAG_MAX = calibrate_mag()
print("Magnetometer calibrated!")
print()
print("MAG_MIN =", MAG_MIN)
print("MAG_MAX =", MAG_MAX)
print("GYRO_CAL =", GYRO_CAL)
