# SPDX-FileCopyrightText: 2020 Jeff Epler for Adafruit Industries
#
# SPDX-License-Identifier: MIT

# pylint: disable=redefined-outer-name,no-self-use,broad-except,try-except-raise,too-many-branches,too-many-statements,unused-import

import gc
import time

from adafruit_display_text.label import Label
from adafruit_hid.keyboard import Keyboard
from adafruit_hid.keyboard_layout_us import KeyboardLayoutUS
from jepler_udecimal import Decimal, getcontext, localcontext
import jepler_udecimal.utrig  # Needed for trig functions in Decimal
import board
import digitalio
import displayio
import framebufferio
import microcontroller
import sharpdisplay
import terminalio

try:
    import usb_hid
except ImportError:
    usb_hid = None

# Initialize the display, cleaning up after a display from the previous
# run if necessary
displayio.release_displays()
framebuffer = sharpdisplay.SharpMemoryFramebuffer(board.SPI(), board.RX, 400, 240)
display = framebufferio.FramebufferDisplay(framebuffer, auto_refresh=False)

def extraprec(add=8, num=0, den=1):
    def inner(fn):
        def wrapper(*args, **kw):
            with localcontext() as ctx:
                ctx.prec = ctx.prec + add + (ctx.prec * num + den - 1) // den
                result = fn(*args, **kw)
            return +result
        return wrapper
    return inner

class AngleConvert:
    def __init__(self):
        self.state = 0

    def next_state(self):
        self.state = (self.state + 1) % 3

    def __str__(self):
        return "DRG"[self.state]

    @property
    def factor(self):
        return [360, None, 400][self.state]

    def from_user(self, x):
        factor = self.factor
        if factor is None:
            return x
        x = x.remainder_near(factor)
        pi_4 = Decimal("1.0").atan()
        return x * pi_4 * 8 / factor

    def to_user(self, x):
        factor = self.factor
        if factor is None:
            return x
        pi_4 = Decimal("1.0").atan()
        return x * factor / pi_4 / 8

    @extraprec(num=1)
    def cos(self, x):
        return self.from_user(x).cos()

    @extraprec(num=1)
    def sin(self, x):
        return self.from_user(x).sin()

    @extraprec(num=1)
    def tan(self, x):
        return self.from_user(x).tan()

    @extraprec(num=1)
    def acos(self, x):
        return self.to_user(x.acos())

    @extraprec(num=1)
    def asin(self, x):
        return self.to_user(x.asin())

    @extraprec(num=1)
    def atan(self, x):
        return self.to_user(x.atan())

getcontext().prec = 14
getcontext().Emax = 99
getcontext().Emin = -99

def get_pin(x):
    if isinstance(x, microcontroller.Pin):
        return digitalio.DigitalInOut(x)
    return x

class MatrixKeypadBase:
    def __init__(self, row_pins, col_pins):
        self.row_pins = [get_pin(p) for p in row_pins]
        self.col_pins = [get_pin(p) for p in col_pins]
        self.old_state = set()
        self.state = set()

        for r in self.row_pins:
            r.switch_to_input(digitalio.Pull.UP)
        for c in self.col_pins:
            c.switch_to_output(False)

    def scan(self):
        self.old_state = self.state
        state = set()
        for c, cp in enumerate(self.col_pins):
            cp.switch_to_output(False)
            for r, rp in enumerate(self.row_pins):
                if not rp.value:
                    state.add((r, c))
            cp.switch_to_input()
        self.state = state
        return state

    def rising(self):
        old_state = self.old_state
        new_state = self.state

        return new_state - old_state

class LayerSelect:
    def __init__(self, idx=1, next_layer=None):
        self.idx = idx
        self.next_layer = next_layer or self

LL0 = LayerSelect(0)
LL1 = LayerSelect(1)
LS1 = LayerSelect(1, LL0)

class MatrixKeypad:
    def __init__(self, row_pins, col_pins, layers):
        self.base = MatrixKeypadBase(row_pins, col_pins)
        self.layers = layers
        self.layer = LL0
        self.pending = []

    def getch(self):
        if not self.pending:
            self.base.scan()
            for r, c in self.base.rising():
                op = self.layers[self.layer.idx][r][c]
                if isinstance(op, LayerSelect):
                    self.layer = op
                else:
                    self.pending.extend(op)
                    self.layer = self.layer.next_layer

        if self.pending:
            return self.pending.pop(0)

        return None

col_pins = (board.D10, board.D9, board.D6, board.TX)
row_pins = (board.A0, board.A1, board.A2, board.A3, board.A4, board.A5)

BS = '\x7f'
CR = '\n'

layers = (
    (
        ('^', 'l', 'r', LS1),
        ('s', 'c', 't', '/'),
        ('7', '8', '9', '*'),
        ('4', '5', '6', '-'),
        ('1', '2', '3', '+'),
        ('0', '.',  BS,  CR)
    ),

    (
        ('v', 'L', 'R', LL0),
        ('S', 'C', 'T', 'N'),
        ( '',  '',  '',  ''),
        ( '',  '',  '', 'n'),
        ( '',  '',  '',  ''),
        ('=', '@',  BS, '~')
    ),
)


class Impl:
    def __init__(self):
        # incoming keypad
        self.keypad = MatrixKeypad(row_pins, col_pins, layers)

        # outgoing keypresses
        self.keyboard = None
        self.keyboard_layout = None

        g = displayio.Group()

        self.labels = labels = []
        labels.append(Label(terminalio.FONT, scale=2, color=0))
        labels.append(Label(terminalio.FONT, scale=3, color=0))
        labels.append(Label(terminalio.FONT, scale=3, color=0))
        labels.append(Label(terminalio.FONT, scale=3, color=0))
        labels.append(Label(terminalio.FONT, scale=3, color=0))
        labels.append(Label(terminalio.FONT, scale=3, color=0))

        for li in labels:
            g.append(li)

        bitmap = displayio.Bitmap((display.width + 126)//127, (display.height + 126)//127, 1)
        palette = displayio.Palette(1)
        palette[0] = 0xffffff

        tile_grid = displayio.TileGrid(bitmap, pixel_shader=palette)
        bg = displayio.Group(scale=127)
        bg.append(tile_grid)

        g.insert(0, bg)

        display.show(g)

    def getch(self):
        while True:
            time.sleep(.02)
            c = self.keypad.getch()
            if c is not None:
                return c

    def setline(self, i, text):
        li = self.labels[i]
        text = text[:31] or " "
        if text == li.text:
            return
        li.text = text
        li.anchor_point = (0,0)
        li.anchored_position = (1, max(1, 41 * i - 7) + 6)

    def refresh(self):
        pass

    def paste(self, text):
        if self.keyboard is None:
            if usb_hid:
                self.keyboard = Keyboard(usb_hid.devices)
                self.keyboard_layout = KeyboardLayoutUS(self.keyboard)
            else:
                return

        if self.keyboard_layout is None:
            raise ValueError("USB HID not available")
        text = str(text)
        self.keyboard_layout.write(text)
        raise RuntimeError("Pasted")

    def start_redraw(self):
        display.auto_refresh = False

    def end_redraw(self):
        display.auto_refresh = True

    def end(self):
        pass
impl = Impl()

stack = []
entry = []

def do_op(arity, fun):
    if arity > len(stack):
        return "underflow"
    res = fun(*stack[-arity:][::-1])
    del stack[-arity:]
    if isinstance(res, list):
        stack.extend(res)
    elif res is not None:
        stack.append(res)
    return None
angleconvert = AngleConvert()

def roll():
    stack[:] = stack[1:] + stack[:1]

def rroll():
    stack[:] = stack[-1:] + stack[:-1]

def swap():
    stack[-2:] = [stack[-1], stack[-2]]

ops = {
    '\'': (1, lambda x: -x),
    '\\': (2, lambda x, y: x/y),
    '#': (2, lambda x, y: y**(1/x)),
    '*': (2, lambda x, y: y*x),
    '+': (2, lambda x, y: y+x),
    '-': (2, lambda x, y: y-x),
    '/': (2, lambda x, y: y/x),
    '^': (2, lambda x, y: y**x),
    'v': (2, lambda x, y: y**(1/x)),
    '_': (2, lambda x, y: x-y),
    '@': angleconvert.next_state,
    'C': (1, angleconvert.acos),
    'c': (1, angleconvert.cos),
    'L': (1, Decimal.exp),
    'l': (1, Decimal.ln),
    'q': (1, lambda x: x**.5),
    'r': roll,
    'R': rroll,
    'S': (1, angleconvert.asin),
    's': (1, angleconvert.sin),
    '~': swap,
    'T': (1, angleconvert.atan),
    't': (1, angleconvert.tan),
    'n': (1, lambda x: -x),
    'N': (1, lambda x: 1/x),
    '=': (1, impl.paste)
}

def pstack(msg):
    impl.setline(0, f'[{angleconvert}] {msg}')

    for i, reg in enumerate("TZYX"):
        if len(stack) > 3-i:
            val = stack[-4+i]
        else:
            val = ""
        impl.setline(1+i, f"{reg} {val}")

def loop():
    impl.start_redraw()
    pstack(f'{gc.mem_free()} RPN bytes free')
    impl.setline(5, "> " + "".join(entry) + "_")
    impl.refresh()
    impl.end_redraw()

    while True:
        do_pstack = False
        do_pentry = False
        message = ''


        c = impl.getch()
        if c in '\x7f\x08':
            if entry:
                entry.pop()
                do_pentry = True
            elif stack:
                stack.pop()
                do_pstack = True
        if c == '\x1b':
            del entry[:]
            do_pentry = True
        elif c in '0123456789.eE':
            if c == '.' and '.' in entry:
                c = 'e'
            entry.append(c)
            do_pentry = True
        elif c == '\x04':
            break
        elif c in ' \n':
            if entry:
                try:
                    stack.append(Decimal("".join(entry)))
                except Exception as e:
                    message = str(e)
                del entry[:]
            elif c == '\n' and stack:
                stack.append(stack[-1])
            do_pstack = True
        elif c in ops:
            if entry:
                try:
                    stack.append(Decimal("".join(entry)))
                except Exception as e:
                    message = str(e)
                del entry[:]
            op = ops.get(c)
            try:
                if callable(op):
                    message = op() or ''
                else:
                    message = do_op(*op) or ''
            except (KeyboardInterrupt, SystemExit):
                raise
            except Exception as e:
                message = str(e)
            do_pstack = True

        impl.start_redraw()

        if do_pstack:
            pstack(message)
            do_pentry = True

        if do_pentry:
            impl.setline(5, "> " + "".join(entry) + "_")

        if do_pentry or do_pstack:
            impl.refresh()

        impl.end_redraw()

try:
    loop()
finally:
    impl.end()
