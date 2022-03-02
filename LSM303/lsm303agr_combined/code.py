# SPDX-FileCopyrightText: 2019 Bryan Siepert for Adafruit Industries
#
# SPDX-License-Identifier: MIT

from time import sleep
import board
import busio
import adafruit_lsm303_accel
import adafruit_lis2mdl

i2c = busio.I2C(board.SCL, board.SDA)
mag = adafruit_lis2mdl.LIS2MDL(i2c)
accel = adafruit_lsm303_accel.LSM303_Accel(i2c)

while True:
    print("Acceleration (m/s^2): X=%0.3f Y=%0.3f Z=%0.3f"%accel.acceleration)
    print("Magnetometer (micro-Teslas)): X=%0.3f Y=%0.3f Z=%0.3f"%mag.magnetic)
    print("")
    sleep(0.5)
