# SPDX-FileCopyrightText: 2025 Tim Cocks for Adafruit Industries
#
# SPDX-License-Identifier: MIT
import sys
import supervisor


# main loop
while True:
    # check how many bytes are available
    available = supervisor.runtime.serial_bytes_available

    # if there are some bytes available
    if available:
        # read data from the keyboard input
        c = sys.stdin.read(available)
        # print the data that was read
        print(c, end="")
