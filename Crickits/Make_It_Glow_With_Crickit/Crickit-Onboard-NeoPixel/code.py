# SPDX-FileCopyrightText: 2018 Anne Barela for Adafruit Industries
#
# SPDX-License-Identifier: MIT

# Using Crickit's onboard NeoPixel
# See http://www.color-hex.com/ for more colors and find your fav!
from adafruit_crickit import crickit
from adafruit_seesaw.neopixel import NeoPixel

crickit_status_pixel = NeoPixel(crickit.seesaw, 27, 1)  # one NeoPixel pin 27

# Fill them with our favorite color "#0099FF light blue" -> 0x0099FF
crickit_status_pixel.fill(0x0099FF)

while True:
    pass
