import board
import displayio
import keypad
import time
import adafruit_displayio_sh1107
from adafruit_hid.keyboard import Keyboard
from adafruit_hid.keyboard_layout_us import KeyboardLayoutUS
from adafruit_hid.keycode import Keycode
from adafruit_display_text import label
from adafruit_bitmap_font import bitmap_font

try:
    import usb_hid
except ImportError:
    usb_hid = None

K_SQ = "√"
K_CL = "<clear>"
K_FN = "<fn>"
K_PA = "<paste>"

KEYMAP0 = [
    K_CL, K_FN, '%',  '/',
    '7',  '8',  '9',  '*',
    '4',  '5',  '6',  '-',
    '1',  '2',  '3',  '+',
    '0',  '.',  K_SQ, '='
]

KEYMAP1 = [
    K_CL, None, '', '',
    '',   '',   '', '',
    '',   '',   '', '',
    '',   '',   '', '',
    '',   '',   '', K_PA,
]

keymaps = {
    0: KEYMAP0,
    1: KEYMAP1,
}

def lookup(layer, key_number):
    while layer >= 0:
        if (key := keymaps[layer][key_number]) is not None:
            return key
        layer -= 1
    return None

displayio.release_displays()
# oled_reset = board.D9

# Use for I2C
i2c = board.I2C()
display_bus = displayio.I2CDisplay(i2c, device_address=0x3C)

# SH1107 is vertically oriented 64x128
WIDTH = 128
HEIGHT = 64

display = adafruit_displayio_sh1107.SH1107(display_bus, width=WIDTH, height=HEIGHT, rotation=180)

font = bitmap_font.load_font("/digit-16px.pcf")
text_area = label.Label(font, text=" ", line_spacing=0.95)
text_area.y = 8
display.show(text_area)

N = float

unary = {
    K_SQ: lambda a: a**.5,
}

binary = {
    '+': (lambda a, b: a+b, lambda a, b: a * (1+b/100)),
    '-': (lambda a, b: a-b, lambda a, b: a * (1-b/100)),
    '*': (lambda a, b: a*b, lambda a, b: a * (b/100)),
    '/': (lambda a, b: a/b, lambda a, b: a / (b/100)),
}

class Calculator:
    def __init__(self):
        self._number1 = N("0")
        self._number2 = None
        self.trail = []
        self.entry = ""
        self.op = None
        self.keyboard = None
        self.keyboard_layout = None

    def paste(text):
        if self.keyboard is None:
            if usb_hid:
                self.keyboard = Keyboard(usb_hid.devices)
                self.keyboard_layout = KeyboardLayoutUS(keyboard)
            else:
                return

        if self.keyboard_layout is None:
            self.add_trail(f"No USB")
        else:
            text = str(text)
            keyboard_layout.write(text)

            self.add_trail(f"Pasted {text}")


    def add_trail(self, msg):
        self.trail = self.trail[:3] + [str(msg)]
        
    @property
    def number1(self):
        return self._number1

    @number1.setter
    def number1(self, number):
        self._number1 = number
        self.add_trail(number)

    @property
    def number2(self):
        if self.entry == "":
            if self._number2 is not None:
                return self._number2
            return None
        return N(self.entry)

    @number2.setter
    def number2(self, number):
        self._number2 = number
        self.entry = ''

    def clear(self):
        self.number1 = N("0")

    def clear_entry(self):
        self.number2 = None

    def key_pressed(self, k):
        if k == K_CL:
            if self.entry:
                self.entry = self.entry[:-1]
            elif self.number2 is None:
                self.clear()
            else:
                self.clear_entry()

        if len(k) == 1 and k in "0123456789":
            self.entry = self.entry + k

        if k == "." and not "." in self.entry:
            if self.entry == "": self.entry = "0"
            self.entry = self.entry + k

        if k == K_PA:
            if self.number2 is not None:
                paste(self.number2)
            else:
                paste(self.number1)

        if k == "=":
            self.do_binary_op(0)

        if k == "%":
            self.do_binary_op(1)

        if op := unary.get(k):
            self.do_unary_op(op)

        if k in binary:
            if self.number2 is not None:
                if self.op:
                    self.do_binary_op(0)
                else:
                    self.number1 = self.number2
                    self.clear_entry()
            self.op = k

    def do_unary_op(self, op):
        if self.number2 is not None:
            self.number2 = op(self.number2)
        else:
            self.number1 = op(self.number1)

    def do_binary_op(self, i):
        if self.op and self.number2 is not None:
            op = binary[self.op][i]
            self.op = None
            self.number1 = op(self.number1, self.number2)
            self.clear_entry()

    def show(self):
        display.auto_refresh = False

        rows = [""] * 4
        trail = self.trail
        if len(trail) > 0:
            rows[2] = trail[-1]
        if len(trail) > 1:
            rows[1] = trail[-2]
        if len(trail) > 2:
            rows[0] = trail[-3]

        entry_or_number = self.entry or self.number2
        cursor = ' :' if (self.number2 is None or self.entry != "") else ""
        rows[-1] = f"{self.op or ''}{entry_or_number or ''}{cursor}"
        for r in rows: print(r)
        text_area.text = "\n".join(rows)
        display.auto_refresh = True

km=keypad.KeyMatrix(row_pins=(board.A2, board.A1, board.A3, board.A0, board.D0), column_pins=(board.D25, board.D11, board.D12, board.D24))

calculator=Calculator()
calculator.show()

layer = 0
while True:
    if ev := km.events.get():
        key = lookup(layer, ev.key_number)
        if ev.pressed:
            if key == K_FN:
                layer = 1
            try:
                calculator.key_pressed(key)
            except Exception as e:
                calculator.add_trail(e)
            calculator.show()

        elif ev.released:
            if key == K_FN:
                layer = 0
