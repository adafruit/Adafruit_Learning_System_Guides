# SPDX-FileCopyrightText: 2018 Kattni Rembor for Adafruit Industries
#
# SPDX-License-Identifier: MIT

import time
from adafruit_circuitplayground.express import cpx

while True:
    print("Temperature C:", cpx.temperature)
    time.sleep(1)
