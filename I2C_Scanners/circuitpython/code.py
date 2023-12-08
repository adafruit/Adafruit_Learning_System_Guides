# SPDX-FileCopyrightText: 2017 Limor Fried for Adafruit Industries
#
# SPDX-License-Identifier: MIT

# pylint: disable=broad-except, eval-used, unused-import

"""CircuitPython I2C Device Address Scan"""
import time
import board
import busio

# List of potential I2C busses
ALL_I2C = ("board.I2C()", "board.STEMMA_I2C()", "busio.I2C(board.GP1, board.GP0)")

# Determine which busses are valid
found_i2c = []
for name in ALL_I2C:
    try:
        print("Checking {}...".format(name), end="")
        bus = eval(name)
        bus.unlock()
        found_i2c.append((name, bus))
        print("ADDED.")
    except Exception as e:
        print("SKIPPED:", e)

# Scan valid busses
if len(found_i2c):
    print("-" * 40)
    print("I2C SCAN")
    print("-" * 40)
    while True:
        for bus_info in found_i2c:
            name = bus_info[0]
            bus = bus_info[1]

            while not bus.try_lock():
                pass

            print(
                name,
                "addresses found:",
                [hex(device_address) for device_address in bus.scan()],
            )

            bus.unlock()

        time.sleep(2)
else:
    print("No valid I2C bus found.")
