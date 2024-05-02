# SPDX-FileCopyrightText: 2024 Liz Clark for Adafruit Industries
#
# SPDX-License-Identifier: MIT

"""USB Host BFF CircuitPython Example
Read key report from attached keyboard"""


import time
import array
import board
import max3421e
import usb

spi = board.SPI()
cs = board.A1
irq = board.A2

host_chip = max3421e.Max3421E(spi, chip_select=cs, irq=irq)

device = None
vid = None
pid = None
while device is None:
    for d in usb.core.find(find_all=True):
        vid = d.idVendor
        pid = d.idProduct
    device = usb.core.find(idVendor=vid, idProduct=pid)
    time.sleep(1)

device.set_configuration()

print(f"{device.idVendor:04x}:{device.idProduct:04x}: {device.manufacturer} {device.product}")

# Test to see if the kernel is using the device and detach it.
if device.is_kernel_driver_active(0):
    device.detach_kernel_driver(0)

# Boot keyboards have 8 byte reports
buf = array.array("B", [0] * 8)
while True:
    try:
        count = device.read(0x81, buf)
    # pylint: disable=broad-except
    except Exception as e:
        continue
    for i in range(0, 8):
        print(buf[i], end=" ")
    print()
