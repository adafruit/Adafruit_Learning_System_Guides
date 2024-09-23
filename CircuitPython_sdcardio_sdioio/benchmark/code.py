# SPDX-FileCopyrightText: 2020 Jeff Epler for Adafruit Industries
#
# SPDX-License-Identifier: MIT

import time
import os

# pylint: disable=unused-import
import mount_sd # You must create a module mount_sd.py that mounts your sd card!

# First, just write the file 'hello.txt' to the card
with open("/sd/hello.txt", "w") as f:
    print("hello world", file=f)

print()
print("SD card I/O benchmarks")

# Test read and write speed in several scenarios:
#  * 512 or 4096 bytes at a time
#  * Writing 1 time or 16 times
# First write the content to the SD card, then read it back, reporting the
# time taken.
for sz in 512, 4096:
    b = bytearray(sz)
    for i in range(sz):
        b[i] = 0xaa
    for n in (1, 16):
        with open("/sd/hello.bin", "wb") as f:
            t0 = time.monotonic_ns()
            for i in range(n):
                f.write(b)
            t1 = time.monotonic_ns()

        dt = (t1-t0) / 1e9
        print(f"write {len(b)} x {n} in {dt}s {n * len(b) / dt / 1000:.1f}Kb/s")

        with open("/sd/hello.bin", "rb") as f:
            t0 = time.monotonic_ns()
            for i in range(n):
                f.readinto(b)
            t1 = time.monotonic_ns()

        dt = (t1-t0) / 1e9

        print(f"read  {len(b)} x {n} in {dt}s {n * len(b) / dt / 1000:.1f}Kb/s")
        print()

# Test "logging" speed and report the time to write each line.
# Note that in this test the file is not closed or flushed after each
# line, so in the event of power loss some lines would be lost.  However,
# it allows much more frequent logging overall.
#
# If keeping data integrity is your highest concern, follow the logging
# example, not this logging benchmark!
print("logging test")
with open("/sd/log.txt", "wt") as logfile:
    t0 = time.monotonic_ns()
    for i in range(10000):
        t1 = time.monotonic_ns()
        dt = (t1-t0) / 1e9
        print(f"Line {i}, {dt:2f}s elapsed", file=logfile)
t1 = time.monotonic_ns()
dt = (t1-t0) / 1e9

print(f"Logged 10000 lines in {dt} seconds, {dt*100:.0f}us/line")
sz = os.stat('/sd/log.txt')[6]
print(f"{sz} bytes written, {sz/dt/1000:.1f}Kb/s")
