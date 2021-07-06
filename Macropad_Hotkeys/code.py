"""
A fairly straightforward macro/hotkey program for Adafruit MACROPAD.
Macro key setups are stored in the /macros folder (configurable below),
load up just the ones you're likely to use. Plug into computer's USB port,
use dial to select an application macro set, press MACROPAD keys to send
key sequences.
"""

# pylint: disable=import-error, unused-import, too-few-public-methods

import os
import board
import digitalio
import displayio
import neopixel
import rotaryio
import keypad
import terminalio
import usb_hid
from adafruit_display_shapes.rect import Rect
from adafruit_display_text import label
from adafruit_hid.keyboard import Keyboard
from adafruit_hid.keycode import Keycode
from adafruit_hid.keyboard_layout_us import KeyboardLayoutUS


# CONFIGURABLES ------------------------

MACRO_FOLDER = '/macros'


# CLASSES AND FUNCTIONS ----------------

class App:
    """ Class representing a host-side application, for which we have a set
        of macro sequences. """
    def __init__(self, appdata):
        self.name = appdata['name']
        self.macros = appdata['macros']

    def switch(self):
        """ Activate application settings; update OLED labels and LED
            colors. """
        GROUP[13].text = self.name   # Application name
        for i in range(12):
            if i < len(self.macros): # Key in use, set label + LED color
                PIXELS[i] = self.macros[i][0]
                GROUP[i].text = self.macros[i][1]
            else:                    # Key not in use, no label or LED
                PIXELS[i] = 0
                GROUP[i].text = ''
        PIXELS.show()
        DISPLAY.refresh()


# INITIALIZATION -----------------------

DISPLAY = board.DISPLAY
DISPLAY.auto_refresh = False
ENCODER = rotaryio.IncrementalEncoder(board.ENCODER_B, board.ENCODER_A)
PIXELS = neopixel.NeoPixel(board.NEOPIXEL, 12, auto_write=False)
KEYBOARD = Keyboard(usb_hid.devices)
LAYOUT = KeyboardLayoutUS(KEYBOARD)
KEYS = keypad.Keys((board.KEY1, board.KEY2, board.KEY3, board.KEY4, board.KEY5,
                    board.KEY6, board.KEY7, board.KEY8, board.KEY9, board.KEY10,
                    board.KEY11, board.KEY12, board.ENCODER_SWITCH),
                   value_when_pressed=False, pull=True)

# Set up displayio group with all labels
GROUP = displayio.Group(max_size=14)
for KEY_INDEX in range(12):
    x = KEY_INDEX % 3
    y = KEY_INDEX // 3
    GROUP.append(label.Label(terminalio.FONT, text='', color=0xFFFFFF,
                             anchored_position=((DISPLAY.width - 1) * x / 2,
                                                DISPLAY.height - 1 -
                                                (3 - y) * 12),
                             anchor_point=(x / 2, 1.0), max_glyphs=15))
GROUP.append(Rect(0, 0, DISPLAY.width, 12, fill=0xFFFFFF))
GROUP.append(label.Label(terminalio.FONT, text='', color=0x000000,
                         anchored_position=(DISPLAY.width//2, -2),
                         anchor_point=(0.5, 0.0), max_glyphs=30))
DISPLAY.show(GROUP)

# Load all the macro key setups from .py files in MACRO_FOLDER
APPS = []
FILES = os.listdir(MACRO_FOLDER)
FILES.sort()
for FILENAME in FILES:
    if FILENAME.endswith('.py'):
        module = __import__(MACRO_FOLDER + '/' + FILENAME[:-3])
        APPS.append(App(module.app))

if not APPS:
    GROUP[13].text = 'NO MACRO FILES FOUND'
    DISPLAY.refresh()
    while True:
        pass

LAST_POSITION = None
APP_INDEX = 0
APPS[APP_INDEX].switch()


# MAIN LOOP ----------------------------

while True:
    POSITION = ENCODER.position
    if POSITION != LAST_POSITION:
        APP_INDEX = POSITION % len(APPS)
        APPS[APP_INDEX].switch()
        LAST_POSITION = POSITION

    EVENT = KEYS.events.get()
    if EVENT and EVENT.key_number < len(APPS[APP_INDEX].macros):
        SEQUENCE = APPS[APP_INDEX].macros[EVENT.key_number][2]
        if EVENT.pressed:
            if EVENT.key_number < 12:
                PIXELS[EVENT.key_number] = 0xFFFFFF
                PIXELS.show()
            for item in SEQUENCE:
                if isinstance(item, int):
                    if item >= 0:
                        KEYBOARD.press(item)
                    else:
                        KEYBOARD.release(item)
                else:
                    LAYOUT.write(item)
        else:
            # Release any still-pressed modifier keys
            for item in SEQUENCE:
                if isinstance(item, int) and item >= 0:
                    KEYBOARD.release(item)
            if EVENT.key_number < 12:
                PIXELS[EVENT.key_number] = APPS[APP_INDEX].macros[
                    EVENT.key_number][0]
                PIXELS.show()
