import time
import board
import digitalio
import rotaryio
import neopixel
import json
import os

import displayio
import terminalio
from adafruit_display_text import label

import usb_hid
from adafruit_hid.keyboard import Keyboard
from adafruit_hid.keycode import Keycode

#from adafruit_hid.mouse import Mouse
#from adafruit_hid.consumer_control import ConsumerControl
#from adafruit_hid.consumer_control_code import ConsumerControlCode

MACRO_FOLDER = '/'

DISPLAY = board.DISPLAY
ENCODER = rotaryio.IncrementalEncoder(board.ENCODER_B, board.ENCODER_A)
PIXELS = neopixel.NeoPixel(board.NEOPIXEL, 12, auto_write=False)
KEYBOARD = Keyboard(usb_hid.devices)

group = displayio.Group(max_size=10)
text1 = "0123\n4567\n89AB\nCDEF\n1234\n5678\n9AB"
text_area = label.Label(terminalio.FONT, text=text1, color=0xFFFFFF, x=8, y=8)
group.append(text_area)

DISPLAY.show(group)

class key:
    DEBOUNCE_TIME = 1 / 50

    def __init__(self, keyname):
        self.io = digitalio.DigitalInOut(keyname)
        self.io.direction = digitalio.Direction.INPUT
        self.io.pull = digitalio.Pull.UP
        self.last_value = self.io.value # Initial state
        self.last_time = time.monotonic()

    def debounce(self):
        value = self.io.value
        if value != self.last_value:
            now = time.monotonic()
            elapsed = now - self.last_time
            if elapsed >= self.DEBOUNCE_TIME:
                self.last_value = value
                self.last_time = now
                return value
        return None

KEYS = []
for keyname in (board.KEY1, board.KEY2, board.KEY3, board.KEY4, board.KEY5,
                board.KEY6, board.KEY7, board.KEY8, board.KEY9, board.KEY10,
                board.KEY11, board.KEY12, board.ENCODER_SWITCH):
    KEYS.append(key(keyname))


class macro:
    def __init__(self, desc, color, sequence):
        self.desc = desc
        self.color = eval(color)
        self.sequence = sequence
        self.in_order = False
        for key in sequence:
            if key.startswith('-'):
                self.in_order = True
                break

class app:
    def __init__(self, filename):
        with open(filename) as jsonfile:
            json_data = json.load(jsonfile)
            self.name = json_data['name']
            default_color = json_data['color'] if 'color' in json_data else '0'
            self.macros = []
            for mac in json_data['macros']:
                self.macros.append(macro(
                    mac['desc'] if 'desc' in mac else None,
                    mac['color'] if 'color' in mac else default_color,
                    mac['sequence'] if 'sequence' in mac else None))

    def switch(self):
        # Set up LED colors
        PIXELS.fill(0)
        for i, mac in enumerate(self.macros):
            PIXELS[i] = mac.color
        PIXELS.show()
        # DO SCREEN HERE
        text_area.text = self.name


APPS = []
files = os.listdir(MACRO_FOLDER)
files.sort()
for filename in files:
    if filename.endswith('.json'):
        APPS.append(app(filename))

if not len(APPS):
    print('No valid macro files found')
    while True:
        pass

LAST_POSITION = None
APP_INDEX = 0
APPS[APP_INDEX].switch()

while True:
    position = ENCODER.position
    if position != LAST_POSITION:
        APP_INDEX = position % len(APPS)
        APPS[APP_INDEX].switch()
        LAST_POSITION = position

#        PIXELS.fill(0)
#        PIXELS[position % len(APPS)] = 0xFFFFFF
#        PIXELS.show()
#        print(position)

    for i, key in enumerate(KEYS):
        action = key.debounce()
        if action is not None:
            print(i, len(APPS[APP_INDEX].macros))

            if i >= len(APPS[APP_INDEX].macros):
                continue # Ignore if key # exceeds macro list length

            keys = APPS[APP_INDEX].macros[i].sequence
            if action is False: # Key pressed
                print('Press', i)
                if APPS[APP_INDEX].macros[i].in_order:
                    for x in APPS[APP_INDEX].macros[i].sequence:
                        if x.startswith('-'):
                            KEYBOARD.release(eval('Keycode.' + x[1:]))
                        else:
                            KEYBOARD.press(eval('Keycode.' + x))
                else:
                    for x in APPS[APP_INDEX].macros[i].sequence:
                        KEYBOARD.press(eval('Keycode.' + x))
            elif action is True: # Key released
                print('Release', i)
                for x in reversed(APPS[APP_INDEX].macros[i].sequence):
                    if not x.startswith('-'):
                        KEYBOARD.release(eval('Keycode.' + x))


META = ('LEFT_CONTROL', 'CONTROL', 'LEFT_SHIFT', 'SHIFT', 'LEFT_ALT', 'ALT',
        'OPTION', 'LEFT_GUI', 'GUI', 'WINDOWS', 'COMMAND', 'RIGHT_CONTROL',
        'RIGHT_SHIFT', 'RIGHT_ALT', 'RIGHT_GUI', 'modifier_bit')

#>>> print(dir(board))
#['__class__', 'BUTTON', 'DISPLAY', 'ENCODER_A', 'ENCODER_B', 'ENCODER_SWITCH', 'I2C', 'KEY1', 'KEY10', 'KEY11', 'KEY12', 'KEY2', 'KEY3', 'KEY4', 'KEY5', 'KEY6', 'KEY7', 'KEY8', 'KEY9', 'LED', 'MISO', 'MOSI', 'NEOPIXEL', 'OLED_CS', 'OLED_DC', 'OLED_RESET', 'ROTA', 'ROTB', 'SCK', 'SCL', 'SDA', 'SPEAKER', 'SPEAKER_SHUTDOWN', 'SPI']

#>>> print(dir(Keycode))
#['__class__', '__module__', '__name__', '__qualname__', '__bases__', '__dict__', 'C', 'M', 'A', 'B', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z', 'ONE', 'TWO', 'THREE', 'FOUR', 'FIVE', 'SIX', 'SEVEN', 'EIGHT', 'NINE', 'ZERO', 'ENTER', 'RETURN', 'ESCAPE', 'BACKSPACE', 'TAB', 'SPACEBAR', 'SPACE', 'MINUS', 'EQUALS', 'LEFT_BRACKET', 'RIGHT_BRACKET', 'BACKSLASH', 'POUND', 'SEMICOLON', 'QUOTE', 'GRAVE_ACCENT', 'COMMA', 'PERIOD', 'FORWARD_SLASH', 'CAPS_LOCK', 'F1', 'F2', 'F3', 'F4', 'F5', 'F6', 'F7', 'F8', 'F9', 'F10', 'F11', 'F12', 'PRINT_SCREEN', 'SCROLL_LOCK', 'PAUSE', 'INSERT', 'HOME', 'PAGE_UP', 'DELETE', 'END', 'PAGE_DOWN', 'RIGHT_ARROW', 'LEFT_ARROW', 'DOWN_ARROW', 'UP_ARROW', 'KEYPAD_NUMLOCK', 'KEYPAD_FORWARD_SLASH', 'KEYPAD_ASTERISK', 'KEYPAD_MINUS', 'KEYPAD_PLUS', 'KEYPAD_ENTER', 'KEYPAD_ONE', 'KEYPAD_TWO', 'KEYPAD_THREE', 'KEYPAD_FOUR', 'KEYPAD_FIVE', 'KEYPAD_SIX', 'KEYPAD_SEVEN', 'KEYPAD_EIGHT', 'KEYPAD_NINE', 'KEYPAD_ZERO', 'KEYPAD_PERIOD', 'KEYPAD_BACKSLASH', 'APPLICATION', 'POWER', 'KEYPAD_EQUALS', 'F13', 'F14', 'F15', 'F16', 'F17', 'F18', 'F19', 'LEFT_CONTROL', 'CONTROL', 'LEFT_SHIFT', 'SHIFT', 'LEFT_ALT', 'ALT', 'OPTION', 'LEFT_GUI', 'GUI', 'WINDOWS', 'COMMAND', 'RIGHT_CONTROL', 'RIGHT_SHIFT', 'RIGHT_ALT', 'RIGHT_GUI', 'modifier_bit']

#>>> print(eval('Keycode.' + 'COMMAND'))

