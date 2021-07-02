"""
Add description here
"""

# pylint: disable=import-error, unused-import, too-few-public-methods, eval-used

import json
import os
import time
import board
import digitalio
import displayio
import neopixel
import rotaryio
import terminalio
import usb_hid
from adafruit_display_text import label
from adafruit_hid.keyboard import Keyboard
from adafruit_hid.keycode import Keycode

# CONFIGURABLES ------------------------

MACRO_FOLDER = '/macros'

# CLASSES AND FUNCTIONS ----------------

class Key:
    """ Add class doccstring here"""
    DEBOUNCE_TIME = 1 / 50

    def __init__(self, keyname):
        self.pin = digitalio.DigitalInOut(keyname)
        self.pin.direction = digitalio.Direction.INPUT
        self.pin.pull = digitalio.Pull.UP
        self.last_value = self.pin.value # Initial state
        self.last_time = time.monotonic()

    def debounce(self):
        """ Add function docstring here """
        value = self.pin.value
        if value != self.last_value:
            now = time.monotonic()
            elapsed = now - self.last_time
            if elapsed >= self.DEBOUNCE_TIME:
                self.last_value = value
                self.last_time = now
                return value
        return None

class Macro:
    """ Add class doccstring here"""
    def __init__(self, desc, color, sequence):
        self.desc = desc
        self.color = eval(color)
        self.sequence = sequence
        self.in_order = False
        for key in sequence:
            if key.startswith('+') or key.startswith('-'):
                self.in_order = True
                break

class App:
    """ Add class doccstring here"""
    def __init__(self, filename):
        with open(MACRO_FOLDER + '/' + filename) as jsonfile:
            json_data = json.load(jsonfile)
            self.name = json_data['name']
            default_color = json_data['color'] if 'color' in json_data else '0'
            self.macros = []
            for mac in json_data['macros']:
                self.macros.append(Macro(
                    mac['desc'] if 'desc' in mac else None,
                    mac['color'] if 'color' in mac else default_color,
                    mac['sequence'] if 'sequence' in mac else None))

    def switch(self):
        """ Add function docstring here """
        GROUP[12].text = self.name
        for i in range(12):
            if i < len(self.macros):
                PIXELS[i] = self.macros[i].color
                GROUP[i].text = self.macros[i].desc
            else:
                PIXELS[i] = 0
                GROUP[i].text = ''
        PIXELS.show()

# Convert key code name (e.g. "COMMAND") to a numeric value for press/release
def code(name):
    """ Add function doccstring here"""
    return eval('Keycode.' + name.upper())

# INITIALIZATION -----------------------

DISPLAY = board.DISPLAY
ENCODER = rotaryio.IncrementalEncoder(board.ENCODER_B, board.ENCODER_A)
PIXELS = neopixel.NeoPixel(board.NEOPIXEL, 12, auto_write=False)
KEYBOARD = Keyboard(usb_hid.devices)

GROUP = displayio.Group(max_size=13)
for KEY_INDEX in range(12):
    x = KEY_INDEX % 3
    y = KEY_INDEX // 3
    GROUP.append(label.Label(terminalio.FONT, text='', color=0xFFFFFF,
                             anchored_position=((DISPLAY.width - 1) * x / 2,
                                                DISPLAY.height - 1 -
                                                (3 - y) * 11),
                             anchor_point=(x / 2, 1.0), max_glyphs=15))
GROUP.append(label.Label(terminalio.FONT, text='', color=0xFFFFFF,
                         anchored_position=(DISPLAY.width//2, 0),
                         anchor_point=(0.5, 0.0), max_glyphs=30))
DISPLAY.show(GROUP)

KEYS = []
for pin in (board.KEY1, board.KEY2, board.KEY3, board.KEY4, board.KEY5,
            board.KEY6, board.KEY7, board.KEY8, board.KEY9, board.KEY10,
            board.KEY11, board.KEY12, board.ENCODER_SWITCH):
    KEYS.append(Key(pin))

APPS = []
FILES = os.listdir(MACRO_FOLDER)
FILES.sort()
for FILENAME in FILES:
    if FILENAME.endswith('.json'):
        APPS.append(App(FILENAME))

if not APPS:
    print('No valid macro files found')
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

    for KEY_INDEX, KEY in enumerate(KEYS[0: len(APPS[APP_INDEX].macros)]):
        action = KEY.debounce()
        if action is not None:
            keys = APPS[APP_INDEX].macros[KEY_INDEX].sequence
            if action is False: # Macro key pressed
                if APPS[APP_INDEX].macros[KEY_INDEX].in_order:
                    for x in APPS[APP_INDEX].macros[KEY_INDEX].sequence:
                        if x.startswith('+'):   # Press and hold key
                            KEYBOARD.press(code(x[1:]))
                        elif x.startswith('-'): # Release key
                            KEYBOARD.release(code(x[1:]))
                        else:                   # Press and release key
                            KEYBOARD.press(code(x))
                            KEYBOARD.release(code(x))
                else:
                    for x in APPS[APP_INDEX].macros[KEY_INDEX].sequence:
                        KEYBOARD.press(code(x))
            elif action is True: # Macro key released
                # Release all keys in reverse order
                for x in reversed(APPS[APP_INDEX].macros[KEY_INDEX].sequence):
                    if x.startswith('+') or x.startswith('-'):
                        KEYBOARD.release(code(x[1:]))
                    else:
                        KEYBOARD.release(code(x))
