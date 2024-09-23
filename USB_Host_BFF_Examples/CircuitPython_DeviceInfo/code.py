# SPDX-FileCopyrightText: 2024 Scott Shawcroft for Adafruit Industries
#
# SPDX-License-Identifier: MIT

"""USB Host BFF Device Info CircuitPython Example"""

import time
import board
import max3421e
import usb

spi = board.SPI()
cs = board.A1
irq = board.A2

host_chip = max3421e.Max3421E(spi, chip_select=cs, irq=irq)

while True:
    print("Finding devices:")
    for device in usb.core.find(find_all=True):
        # pylint: disable=line-too-long
        print(f"{device.idVendor:04x}:{device.idProduct:04x}: {device.manufacturer} {device.product}")
    time.sleep(5)
