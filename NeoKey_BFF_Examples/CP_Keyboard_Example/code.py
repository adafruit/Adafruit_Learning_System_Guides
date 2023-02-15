# SPDX-FileCopyrightText: 2023 Liz Clark for Adafruit Industries
#
# SPDX-License-Identifier: MIT

"""Basic HID Macro with NeoKey BFF Example"""
import time
import board
from digitalio import DigitalInOut, Direction, Pull
import neopixel
import usb_hid
from adafruit_hid.keyboard import Keyboard
from adafruit_hid.keycode import Keycode

# setup onboard NeoPixel
pixel_pin = board.A3
num_pixels = 1
pixel_color = (0, 255, 0)
off = (0, 0, 0)

pixels = neopixel.NeoPixel(pixel_pin, num_pixels, brightness=0.3, auto_write=False)

# The Keycode sent for each button, will be paired with a control key
key = Keycode.F
modifier_key = Keycode.CONTROL

# The keyboard object!
time.sleep(1)  # Sleep for a bit to avoid a race condition on some systems
keyboard = Keyboard(usb_hid.devices)

# setup onboard button
switch = DigitalInOut(board.A2)
switch.direction = Direction.INPUT
switch.pull = Pull.UP
switch_state = False

while True:

    # if the button is not pressed..
    if switch.value and switch_state:
        pixels.fill(off)
        pixels.show()
        keyboard.release_all()
        switch_state = False

    # if the button is pressed..
    if not switch.value and not switch_state:
        # neopixel brightness is 0.3 and rainbow animation is visible
        pixels.fill(pixel_color)
        pixels.show()
        keyboard.press(modifier_key, key)
        switch_state = True
