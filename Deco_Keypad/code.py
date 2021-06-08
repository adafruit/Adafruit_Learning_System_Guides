# SPDX-FileCopyrightText: Copyright (c) 2021 John Park for Adafruit
#
# SPDX-License-Identifier: MIT
# Deco Keypad


import time
import board
from digitalio import DigitalInOut, Pull
from adafruit_debouncer import Debouncer
import usb_hid
from adafruit_hid.keyboard import Keyboard
from adafruit_hid.keyboard_layout_us import KeyboardLayoutUS
from adafruit_hid.keycode import Keycode
import neopixel

print("- Deco Keypad -")
time.sleep(1)  # Sleep for a bit to avoid a race condition on some systems

#  ----- Keymap -----  #
# change as needed, e.g. capital A (Keycode.SHIFT, Keycode.A)
switch_a_output = Keycode.Z
switch_b_output = Keycode.X

#  ----- Keyboard setup -----  #
keyboard = Keyboard(usb_hid.devices)
keyboard_layout = KeyboardLayoutUS(keyboard)  # We're in the US :)

# ----- Key setup ----- #
switch_a_in = DigitalInOut(board.D5)
switch_b_in = DigitalInOut(board.D6)
switch_a_in.pull = Pull.UP
switch_b_in.pull = Pull.UP
switch_a = Debouncer(switch_a_in)
switch_b = Debouncer(switch_b_in)

# ----- NeoPixel setup ----- #
MAGENTA = 0xFF00FF
CYAN = 0x0088DD
WHITE = 0xCCCCCC
BLACK = 0x000000

pixel_pin = board.D9
pixels = neopixel.NeoPixel(pixel_pin, 2, brightness=1.0)
pixels.fill(BLACK)
time.sleep(0.3)
pixels.fill(WHITE)
time.sleep(0.3)
pixels.fill(BLACK)
time.sleep(0.3)
pixels[0] = MAGENTA
pixels[1] = CYAN


while True:
    switch_a.update()  # Debouncer checks for changes in switch state
    switch_b.update()

    if switch_a.fell:
        keyboard.press(switch_a_output)
        pixels[0] = WHITE
    if switch_a.rose:
        keyboard.release(switch_a_output)
        pixels[0] = MAGENTA

    if switch_b.fell:
        keyboard.press(switch_b_output)
        pixels[1] = WHITE
    if switch_b.rose:
        keyboard.release(switch_b_output)
        pixels[1] = CYAN
