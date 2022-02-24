# SPDX-FileCopyrightText: 2021 Kattni Rembor for Adafruit Industries
#
# SPDX-License-Identifier: MIT

"""NeoKey Trinkey Capacitive Touch and HID Keyboard example"""
import time
import board
import neopixel
import usb_hid
from adafruit_hid.keyboard import Keyboard
from adafruit_hid.keyboard_layout_us import KeyboardLayoutUS
from adafruit_hid.keycode import Keycode  # pylint: disable=unused-import
from digitalio import DigitalInOut, Pull
import touchio

print("NeoKey Trinkey HID")

# create the pixel and turn it off
pixel = neopixel.NeoPixel(board.NEOPIXEL, 1, brightness=0.1)
pixel.fill(0x0)

time.sleep(1)  # Sleep for a bit to avoid a race condition on some systems
keyboard = Keyboard(usb_hid.devices)
keyboard_layout = KeyboardLayoutUS(keyboard)  # We're in the US :)

# create the switch, add a pullup, start it with not being pressed
button = DigitalInOut(board.SWITCH)
button.switch_to_input(pull=Pull.DOWN)
button_state = False

# create the captouch element and start it with not touched
touch = touchio.TouchIn(board.TOUCH)
touch_state = False

# print a string on keypress
key_output = "Hello World!\n"

# one character on keypress
# key_output = Keycode.A

# multiple simultaneous keypresses
# key_output = (Keycode.SHIFT, Keycode.A)  # capital A
# key_output = (Keycode.CONTROL, Keycode.ALT, Keycode.DELETE) # three finger salute!

# complex commands! we make a list of dictionary entries for each command
# each line has 'keys' which is either a single key, a list of keys, or a string
# then the 'delay' is in seconds, since we often need to give the computer a minute
# before doing something!

# this will open up a notepad in windows, and ducky the user
"""
key_output = (
   {'keys': Keycode.GUI, 'delay': 0.1},
   {'keys': "notepad\n", 'delay': 1},  # give it a moment to launch!
   {'keys': "YOU HAVE BEEN DUCKIED!", 'delay': 0.1},
   {'keys': (Keycode.ALT, Keycode.O), 'delay': 0.1}, # open format menu
   {'keys': Keycode.F, 'delay': 0.1}, # open font submenu
   {'keys': "\t\t100\n", 'delay': 0.1}, # tab over to font size, enter 100
)
"""


# our helper function will press the keys themselves
def make_keystrokes(keys, delay):
    if isinstance(keys, str):  # If it's a string...
        keyboard_layout.write(keys)  # ...Print the string
    elif isinstance(keys, int):  # If its a single key
        keyboard.press(keys)  # "Press"...
        keyboard.release_all()  # ..."Release"!
    elif isinstance(keys, (list, tuple)):  # If its multiple keys
        keyboard.press(*keys)  # "Press"...
        keyboard.release_all()  # ..."Release"!
    time.sleep(delay)


while True:
    if button.value and not button_state:
        pixel.fill((255, 0, 255))
        print("Button pressed.")
        button_state = True

    if not button.value and button_state:
        pixel.fill(0x0)
        print("Button released.")
        if isinstance(key_output, (list, tuple)) and isinstance(key_output[0], dict):
            for k in key_output:
                make_keystrokes(k['keys'], k['delay'])
        else:
            make_keystrokes(key_output, delay=0)
        button_state = False

    if touch.value and not touch_state:
        print("Touched!")
        pixel.fill((0, 255, 0))
        touch_state = True
    if not touch.value and touch_state:
        print("Untouched!")
        pixel.fill(0x0)
        touch_state = False
