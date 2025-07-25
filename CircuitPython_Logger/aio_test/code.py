# SPDX-FileCopyrightText: 2019 Dave Astels for Adafruit Industries
#
# SPDX-License-Identifier: MIT

import time
import random
from adafruit_pyportal import PyPortal
from aio_handler import AIOHandler
import adafruit_logging as logging

device = PyPortal()

l = logging.getLogger("aio")
l.addHandler(AIOHandler("test", device))

while True:
    t = random.randint(1, 5)
    if t == 1:
        print("debug")
        l.debug("debug message: %d", random.randint(0, 1000))
    elif t == 2:
        print("info")
        l.info("info message: %d", random.randint(0, 1000))
    elif t == 3:
        print("warning")
        l.warning("warning message: %d", random.randint(0, 1000))
    elif t == 4:
        print("error")
        l.error("error message: %d", random.randint(0, 1000))
    elif t == 5:
        print("critical")
        l.critical("critical message: %d", random.randint(0, 1000))
    time.sleep(5.0 + (random.random() * 5.0))
