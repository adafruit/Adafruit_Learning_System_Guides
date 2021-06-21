"""NeoKey Trinkey Capacitive Touch and HID Keyboard example"""
import time
import board
import neopixel
import usb_hid
from adafruit_hid.keyboard import Keyboard
from adafruit_hid.keyboard_layout_us import KeyboardLayoutUS
from adafruit_hid.keycode import Keycode  # pylint: disable=unused-import
from adafruit_hid.mouse import Mouse
from digitalio import DigitalInOut, Pull
import touchio
import random
import math

mouse = Mouse(usb_hid.devices)
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

key_output = (
   {'keys': Keycode.GUI, 'delay': 0.1},
   {'keys': "notepad\n", 'delay': 1},  # give it a moment to launch!
   {'keys': "YOU HAVE BEEN DUCKIED!", 'delay': 0.1},
   {'keys': (Keycode.ALT, Keycode.O), 'delay': 0.1}, # open format menu
   {'keys': Keycode.F, 'delay': 0.1}, # open font submenu
   {'keys': "\t\t100\n", 'delay': 0.1}, # tab over to font size, enter 100
)

ssid = ""
password = ""

account = ""
account_password = ""

DELAY = 0.05
key_output = (
   {'keys': None, 'delay': 2}, # Wifi setup
   {'keys': Keycode.TAB, 'delay': DELAY},
   {'keys': Keycode.TAB, 'delay': DELAY},
   {'keys': Keycode.TAB, 'delay': DELAY},
   {'keys': Keycode.TAB, 'delay': DELAY},
   {'keys': Keycode.ENTER, 'delay': 1},
   {'keys': Keycode.TAB, 'delay': DELAY},
   {'keys': Keycode.TAB, 'delay': DELAY},
   {'keys': Keycode.TAB, 'delay': DELAY},
   {'keys': Keycode.ENTER, 'delay': 0.5},
   {'keys': ssid, 'delay': 0.5},
   {'keys': Keycode.TAB, 'delay': 0.5},
   {'keys': Keycode.DOWN_ARROW, 'delay': DELAY},
   {'keys': Keycode.DOWN_ARROW, 'delay': 0.5},
   {'keys': Keycode.TAB, 'delay': DELAY},
   {'keys': password, 'delay': 0.5},
   {'keys': Keycode.ENTER, 'delay': 9}, # Long pause while connection is established
   {'keys': Keycode.TAB, 'delay': DELAY}, # Go Through first run setup
   {'keys': Keycode.TAB, 'delay': DELAY},
   {'keys': Keycode.ENTER, 'delay': 0.5},
   {'keys': Keycode.TAB, 'delay': DELAY},
   {'keys': Keycode.TAB, 'delay': DELAY},
   {'keys': Keycode.TAB, 'delay': DELAY},
   {'keys': Keycode.ENTER, 'delay': 0.5},
   {'keys': (Keycode.CONTROL, Keycode.ALT, Keycode.E), 'delay': DELAY},
   {'keys': Keycode.TAB, 'delay': DELAY},
   {'keys': Keycode.TAB, 'delay': DELAY},
   {'keys': Keycode.TAB, 'delay': DELAY},
   {'keys': Keycode.TAB, 'delay': DELAY},
   {'keys': Keycode.TAB, 'delay': DELAY}, # Part Two: Enrollment
   {'keys': Keycode.ENTER, 'delay': 4},
   {'keys': account, 'delay': DELAY},
   {'keys': Keycode.ENTER, 'delay': 5},
   {'keys': account_password, 'delay': 0.5},
   {'keys': Keycode.ENTER, 'delay': 8}, # Long pause while device is enrolled
   {'keys': Keycode.ENTER, 'delay': DELAY},
)

def make_keystrokes(keys, delay):
    start = time.monotonic()
    if isinstance(keys, str):  # If it's a string...
        keyboard_layout.write(keys)  # ...Print the string
        print(keys)
    elif isinstance(keys, int):  # If its a single key
        keyboard.press(keys)  # "Press"...
        pixel.fill((math.sin(keys)*255, math.cos(keys)*255, math.tan(keys)*255))
        keyboard.release_all()  # ..."Release"!
        print(keys)
    elif isinstance(keys, (list, tuple)):  # If its multiple keys
        keyboard.press(*keys)  # "Press"...
        for key in keys:
            pixel.fill((math.sin(key)*255, math.cos(key)*255, math.tan(key)*255))
        keyboard.release_all()  # ..."Release"!
        print(*keys)
    while time.monotonic() < start + delay:
        if button.value:
            print("Stopped")
            return

activated = False
while True:
    if button.value:
        activated = True
        time.sleep(0.5)
        pixel.fill(0x000000)
    if activated:
        print("Starting")
        for k in key_output:
            if button.value:
                activated = False
                time.sleep(0.2)
                break
            make_keystrokes(k['keys'], k['delay'])
        print("Done!")
        pixel.fill(0xFFFFFF)
        time.sleep(0.1)
        pixel.fill(0x000000)
        time.sleep(0.1)
        pixel.fill(0xFFFFFF)
        time.sleep(0.1)
        pixel.fill(0x000000)
        time.sleep(0.1)
        pixel.fill(0xFFFFFF)
        break
