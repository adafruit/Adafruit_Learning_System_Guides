# SPDX-FileCopyrightText: 2022 Kattni Rembor for Adafruit Industries
# SPDX-License-Identifier: MIT
"""
CircuitPython Simple Example for LC709203 Sensor
"""
import time
import board
from adafruit_lc709203f import LC709203F, PackSize

# Create sensor object, using the board's default I2C bus.
battery_monitor = LC709203F(board.I2C())

# Update to match the mAh of your battery for more accurate readings.
# Can be MAH100, MAH200, MAH400, MAH500, MAH1000, MAH2000, MAH3000.
# Choose the closest match. Include "PackSize." before it, as shown.
battery_monitor.pack_size = PackSize.MAH400

while True:
    print("Battery Percent: {:.2f} %".format(battery_monitor.cell_percent))
    print("Battery Voltage: {:.2f} V".format(battery_monitor.cell_voltage))
    time.sleep(2)
