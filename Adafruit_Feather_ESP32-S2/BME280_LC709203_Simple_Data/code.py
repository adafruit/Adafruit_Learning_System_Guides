# SPDX-FileCopyrightText: 2021 Kattni Rembor for Adafruit Industries
# SPDX-License-Identifier: Unlicense
"""
CircuitPython Simple Example for BME280 and LC709203 Sensors
"""
import time
import board
import digitalio
from adafruit_bme280 import basic as adafruit_bme280
from adafruit_lc709203f import LC709203F, PackSize

# Create sensor objects, using the board's default I2C bus.
i2c = board.I2C()
bme280 = adafruit_bme280.Adafruit_BME280_I2C(i2c)
battery_monitor = LC709203F(board.I2C())
battery_monitor.pack_size = PackSize.MAH400

# change this to match your location's pressure (hPa) at sea level
bme280.sea_level_pressure = 1013.25

while True:
    print("\nTemperature: {:.1f} C".format(bme280.temperature))
    print("Humidity: {:.1f} %".format(bme280.relative_humidity))
    print("Pressure: {:.1f} hPa".format(bme280.pressure))
    print("Altitude: {:.2f} meters".format(bme280.altitude))
    print("Battery Percent: {:.2f} %".format(battery_monitor.cell_percent))
    print("Battery Voltage: {:.2f} V".format(battery_monitor.cell_voltage))
    time.sleep(2)
