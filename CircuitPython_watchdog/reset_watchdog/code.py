# SPDX-FileCopyrightText: 2026 Tim Cocks for Adafruit Industries
#
# SPDX-License-Identifier: MIT
"""
Demonstration of RESET mode watchdog. Supported on:
raspberrypi, nordic, espressif, and samd51 devices.

Resets the device if the watchdog is not fed at least once per timeout interval.

On nordic port the device boots into safe mode after the reset.
"""
import microcontroller
import watchdog

print(microcontroller.cpu.reset_reason)

wdt = microcontroller.watchdog

# must feed the watchdog at least once every interval of this many seconds
wdt.timeout = 8

# activate the watchdog is reset mode
wdt.mode = watchdog.WatchDogMode.RESET


while True:
    wdt.feed()

    # other tasks for you project...
