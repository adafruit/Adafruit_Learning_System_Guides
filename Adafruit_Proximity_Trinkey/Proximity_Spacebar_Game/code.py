# SPDX-FileCopyrightText: 2021 Kattni Rembor for Adafruit Industries
#
# SPDX-License-Identifier: MIT

"""
Proximity spacebar dino game example. Sends a space when you move your hand close to the proximity
sensor and turns the LEDs on to let you know you're in the right range. For use with the Chrome
Dino game, reachable in Chrome with chrome://dino or when you have no network connectivity.
"""
import board
import usb_hid
from adafruit_hid.keyboard import Keyboard
from adafruit_hid.keycode import Keycode
import neopixel
from adafruit_apds9960.apds9960 import APDS9960

apds = APDS9960(board.I2C())
pixels = neopixel.NeoPixel(board.NEOPIXEL, 2)
keyboard = Keyboard(usb_hid.devices)

apds.enable_proximity = True

space = False
while True:
    print(apds.proximity)
    current_proximity = apds.proximity
    if current_proximity > 100 and not space:
        pixels.fill((255, 0, 0))
        keyboard.send(Keycode.SPACE)
        space = True
    elif current_proximity < 50 and space:
        pixels.fill(0)
        space = False
