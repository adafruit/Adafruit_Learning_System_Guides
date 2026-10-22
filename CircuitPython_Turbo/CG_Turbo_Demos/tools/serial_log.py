#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 John Park with Claude Opus 5.5 for Adafruit Industries
#
# SPDX-License-Identifier: MIT
"""Print the Fruit Jam's serial console for a while.

    python3 tools/serial_log.py --seconds 20 --restart

--restart sends Ctrl-C then Ctrl-D so code.py starts fresh while we listen.
"""

import argparse
import sys
import time

import serial
from serial.tools import list_ports

ADAFRUIT_VID = 0x239A


def find_port():
    ports = [p.device for p in list_ports.comports() if p.vid == ADAFRUIT_VID]
    if not ports:
        sys.exit("no Adafruit serial port found")
    return ports[0]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--port")
    parser.add_argument("--seconds", type=float, default=15)
    parser.add_argument("--restart", action="store_true")
    options = parser.parse_args()
    with serial.Serial(options.port or find_port(), 115200, timeout=0.1) as port:
        if options.restart:
            port.write(b"\x03")
            time.sleep(0.3)
            port.write(b"\x04")
        end = time.monotonic() + options.seconds
        while time.monotonic() < end:
            data = port.read(4096)
            if data:
                sys.stdout.write(data.decode("utf-8", "replace"))
                sys.stdout.flush()


if __name__ == "__main__":
    main()
