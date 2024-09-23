# SPDX-FileCopyrightText: Copyright (c) 2020 ladyada for Adafruit Industries
#
# SPDX-License-Identifier: MIT

import time
import math
import board
import adafruit_sht4x

i2c = board.I2C()  # uses board.SCL and board.SDA
sht = adafruit_sht4x.SHT4x(i2c)
sht.mode = adafruit_sht4x.Mode.NOHEAT_HIGHPRECISION

while True:
    temperature, relative_humidity = sht.measurements
    # saturation vapor pressure is calculated
    svp = 0.6108 * math.exp(17.27 * temperature / (temperature + 237.3))
    # actual vapor pressure
    avp = relative_humidity / 100 * svp
    # VPD = saturation vapor pressure - actual vapor pressure
    vpd = svp - avp
    print(f"Vapor-Pressure Deficit: {vpd:0.1f} kPa")
    time.sleep(1)
