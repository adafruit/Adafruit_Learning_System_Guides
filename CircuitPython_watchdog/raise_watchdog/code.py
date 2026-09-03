# SPDX-FileCopyrightText: 2026 Tim Cocks for Adafruit Industries
#
# SPDX-License-Identifier: MIT
"""
Demonstration of the RAISE mode watchdog. Supported on nordic, and espressif ports only.

Raises an exception if the watchdog is not fed at least once every timeout interval.
"""
import microcontroller
import watchdog


wdt = microcontroller.watchdog

# must feed the watchdog at least once every interval of this many seconds
wdt.timeout = 8

# activate the watchdog is raise mode
wdt.mode = watchdog.WatchDogMode.RAISE


while True:
    wdt.feed()

    # other tasks for you project...
