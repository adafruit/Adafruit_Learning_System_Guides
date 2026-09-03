# SPDX-FileCopyrightText: 2026 Tim Cocks for Adafruit Industries
#
# SPDX-License-Identifier: MIT
"""
Demonstrates how to use the RAISE mode watchdog on Nordic to match the
non-safemode RESET behavior that non-Nordic ports have.
"""
import time

import microcontroller
import watchdog

# will indicate SOFTWARE, not WATCHDOG since the code manually resets
print(microcontroller.cpu.reset_reason)

wdt = microcontroller.watchdog

# must feed the watchdog at least once every interval of this many seconds
wdt.timeout = 8

# activate the watchdog is raise mode
wdt.mode = watchdog.WatchDogMode.RAISE

# wrap main loop in try/except to catch the WatchDogTimeout
try:
    while True:
        pass
except watchdog.WatchDogTimeout:
    print("Watchdog bit, doing normal mode reset in 3 seconds")
    time.sleep(3)
    # normal non-safemode reset
    microcontroller.reset()
