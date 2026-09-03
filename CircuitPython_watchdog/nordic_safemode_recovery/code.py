# SPDX-FileCopyrightText: 2026 Tim Cocks for Adafruit Industries
#
# SPDX-License-Identifier: MIT
"""
Demonstration of RESET mode watchdog on nordic, with safemode.py recovery file.

The watchdog resets the device into safemode if not fed at least once per
timeout interval. safemode.py resets again back into normal mode.
"""
import time
import microcontroller
import watchdog

# wait a few seconds before activating, to give time to cancel.
time.sleep(5)

print(microcontroller.cpu.reset_reason)

wdt = microcontroller.watchdog

# must feed the watchdog at least once every interval of this many seconds
wdt.timeout = 8

# activate the watchdog is reset mode
wdt.mode = watchdog.WatchDogMode.RESET

while True:
    wdt.feed()

    # other tasks for you project...
