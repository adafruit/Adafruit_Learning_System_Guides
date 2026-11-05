#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 John Park for Adafruit Industries
#
# SPDX-License-Identifier: GPL-3.0-only
"""Print a USB device's configuration descriptor summary (pyusb + libusb).

  usb_descriptors.py [VID:PID]     default 4c4a:c755 (FM-1, stock V15)
"""
import sys

import usb.core
import usb.util

vid, pid = (int(x, 16) for x in (sys.argv[1] if len(sys.argv) > 1 else "4c4a:c755").split(":"))
dev = usb.core.find(idVendor=vid, idProduct=pid)
if dev is None:
    sys.exit("no %04x:%04x attached" % (vid, pid))
print("%04x:%04x %s / %s, class %02x, configs %d" % (
    vid, pid, usb.util.get_string(dev, dev.iManufacturer), usb.util.get_string(dev, dev.iProduct),
    dev.bDeviceClass, dev.bNumConfigurations))
for cfg in dev:
    raw = dev.ctrl_transfer(0x80, 6, (2 << 8) | (cfg.index if hasattr(cfg, "index") else 0), 0, cfg.wTotalLength)
    print("config %d: wTotalLength %d bytes, %d interfaces" % (cfg.bConfigurationValue, cfg.wTotalLength, cfg.bNumInterfaces))
    for intf in cfg:
        eps = ", ".join("0x%02x %s %d" % (e.bEndpointAddress, ("ctrl", "iso", "bulk", "int")[e.bmAttributes & 3],
                                          e.wMaxPacketSize) for e in intf)
        print("  if %d alt %d class %02x/%02x  %s" % (intf.bInterfaceNumber, intf.bAlternateSetting,
                                                    intf.bInterfaceClass, intf.bInterfaceSubClass, eps))
    print("  raw:", bytes(raw).hex())
