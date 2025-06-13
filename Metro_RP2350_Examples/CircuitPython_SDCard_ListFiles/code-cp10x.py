# SPDX-FileCopyrightText: 2017 Limor Fried for Adafruit Industries
# SPDX-License-Identifier: MIT

"""
CircuitPython 10.x SD Card Directory Listing Demo
Assumes the SD card is auto-mounted at /sd by the runtime.
"""

import os

def print_directory(path, tabs=0):
    for name in os.listdir(path):
        full_path = f"{path}/{name}"
        stats     = os.stat(full_path)
        filesize  = stats[6]
        isdir     = bool(stats[0] & 0x4000)

        # human-readable size
        if   filesize < 1_000:
            sizestr = f"{filesize} bytes"
        elif filesize < 1_000_000:
            sizestr = f"{filesize/1_000:.1f} KB"
        else:
            sizestr = f"{filesize/1_000_000:.1f} MB"

        indent       = "   " * tabs
        display_name = indent + name + ("/" if isdir else "")

        # <40 pads or truncates to 40 chars, then we append the size
        print(f"{display_name:<40} Size: {sizestr}")

        if isdir:
            print_directory(full_path, tabs + 1)

print("Files on /sd:")
print("====================")
print_directory("/sd")
