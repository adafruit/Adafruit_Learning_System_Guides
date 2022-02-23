# SPDX-FileCopyrightText: 2018 Kattni Rembor for Adafruit Industries
#
# SPDX-License-Identifier: MIT

from adafruit_circuitplayground.express import cpx

cpx.detect_taps = 2

while True:
    if cpx.tapped:
        print("Tapped!")
