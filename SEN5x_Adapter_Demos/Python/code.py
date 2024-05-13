# SPDX-FileCopyrightText: 2024 Liz Clark for Adafruit Industries
#
# SPDX-License-Identifier: MIT

import time
from sensirion_i2c_driver import I2cConnection, LinuxI2cTransceiver
from sensirion_i2c_sen5x import Sen5xI2cDevice

i2c = LinuxI2cTransceiver('/dev/i2c-1')
device = Sen5xI2cDevice(I2cConnection(i2c))

# Print some device information
print(f"Version: {device.get_version()}")
print(f"Product Name: {device.get_product_name()}")
print(f"Serial Number: {device.get_serial_number()}")

# Perform a device reset (reboot firmware)
device.device_reset()
# Start measurement
device.start_measurement()
time.sleep(1)

def read_data():
    try:
        # Wait until next result is available
        print("Waiting for new data...")
        while device.read_data_ready() is False:
            time.sleep(0.1)
        # Read measured values -> clears the "data ready" flag
        values = device.read_measured_values()
        print(values)
        # Access a specific value separately (see Sen5xMeasuredValues)
        # mass_concentration = values.mass_concentration_2p5.physical
        # ambient_temperature = values.ambient_temperature.degrees_celsius
        # Read device status
        status = device.read_device_status()
        print("Device Status: {}\n".format(status))
    except Exception as e: # pylint: disable = broad-except
        print(f"Error: {e}")

while True:
    read_data()
    time.sleep(5)
