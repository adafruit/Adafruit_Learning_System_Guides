# SPDX-FileCopyrightText: 2021 ladyada for Adafruit Industries
# SPDX-License-Identifier: MIT
#
# BNO055 + BMP280 BFF Demo

import time
import board
import adafruit_bno055
import adafruit_bmp280

i2c = board.I2C()  # uses board.SCL and board.SDA
bno055 = adafruit_bno055.BNO055_I2C(i2c)

bmp280 = adafruit_bmp280.Adafruit_BMP280_I2C(i2c)
bmp280.sea_level_pressure = 1013.25

while True:
    print(f"Temperature: {bmp280.temperature:0.1f} C")
    print(f"Pressure: {bmp280.pressure:0.1f} hPa")
    print(f"Altitude = {bmp280.altitude:0.2f} meters")
    print(f"Accelerometer (m/s^2): {bno055.acceleration}")
    print(f"Magnetometer (microteslas): {bno055.magnetic}")
    print(f"Gyroscope (rad/sec): {bno055.gyro}")
    print(f"Euler angle: {bno055.euler}")
    print(f"Quaternion: {bno055.quaternion}")
    print(f"Linear acceleration (m/s^2): {bno055.linear_acceleration}")
    print(f"Gravity (m/s^2): {bno055.gravity}")
    print()

    time.sleep(1)
