# SPDX-FileCopyrightText: 2022 Jeff Epler for Adafruit Industries
# SPDX-License-Identifier: MIT

# Commodore 16 to USB HID adapter with Adafruit KB2040
#
# Note that:
#  * This matrix is different than the (more common) Commodore 64 matrix
#  * There are no diodes, not even on modifiers, so there's only 2-key rollover.

import asyncio.core
import board
import keypad
from adafruit_hid.keycode import Keycode as K
from adafruit_hid.keyboard import Keyboard
import usb_hid

# True to use a more POSITIONAL mapping, False to use a more PC-style mapping
POSITIONAL = True

# Keyboard schematic from
# https://archive.org/details/SAMS_Computerfacts_Commodore_C16_1984-12_Howard_W_Sams_Co_CC8/page/n9/mode/2up
# 1  3  6  7  8  9  10 11 12  13   14   15  16 17 18 19  # connector pins
# R5 C7 R7 C4 R1 C5 C6 R3 R2  R4   C2   C1  R6 C3 C0 R0  # row/column in schematic
# D2 D3 D4 D5 D6 D7 D8 D9 D10 MOSI MISO SCK A0 A1 A2 A3  # conencted to kb2040 at
# results in the the following assignment of rows and columns:
rows = [board.A3, board.D6, board.D10, board.D9, board.MOSI, board.D2, board.A0, board.D4]
cols = [board.A2, board.SCK, board.MISO, board.A1, board.D5, board.D7, board.D8, board.D3]

# ROM listing of key values from ed7.src in
# http://www.zimmers.net/anonftp/pub/cbm/src/plus4/ted_kernal_basic_src.tar.gz
# shows key matrix arrangement (it's nuts)
# del   return  £       f8      f1      f2      f3      @
# 3     w       a       4       z       s       e       shift
# 5     r       d       6       c       f       t       x
# 7     y       g       8       b       h       u       v
# 9     i       j       0       m       k       o       n
# down  p       l       up      .       :       -       ,
# left  *       ;       right   escape  =       +       /
# 1     home    control 2       space   c=key   q       stop

# Implement an FN-key for some keys not present on the default keyboard
class FnState:
    def __init__(self):
        self.state = False

    def fn_event(self, event):
        self.state = event.pressed

    def fn_modify(self, keycode):
        if self.state:
            return self.mods.get(keycode, keycode)
        return keycode

    mods = {
            K.ONE: K.F1,
            K.TWO: K.F2,
            K.THREE: K.F3,
            K.FOUR: K.F4,
            K.FIVE: K.F5,
            K.SIX: K.F6,
            K.SEVEN: K.F7,
            K.EIGHT: K.F8,
            K.NINE: K.F9,
            K.ZERO: K.F10,
            K.F1: K.F11,
            K.F2: K.F12,
            K.UP_ARROW: K.PAGE_UP,
            K.DOWN_ARROW: K.PAGE_DOWN,
            K.LEFT_ARROW: K.HOME,
            K.RIGHT_ARROW: K.END,
            K.BACKSPACE: K.DELETE,
            K.F3: K.INSERT,
    }
fn_state = FnState()

K_FN = fn_state.fn_event

# A tuple is special, it:
# * Clears shift modifiers & pressed keys
# * Presses the given sequence
# * Releases all pressed keys
# * Restores the original modifiers
# It's mostly used to send a key that requires a shift keypress on a standard
# keyboard (or which is mapped to a shifted key but requires that shift NOT
# be pressed)
#
# A consequence of this is that the key will not repeat, even if it is held
# down.  So for example in the positional mapping, shift-1 will repeat "!"
# but shift-7 will not repeat "'" and shift-0 will not repeat "^".
K_AT = (K.SHIFT, K.TWO)
K_PLUS = (K.SHIFT, K.EQUALS)
K_ASTERISK = (K.SHIFT, K.EIGHT)
K_COLON = (K.SHIFT, K.SEMICOLON)

# We need these mask values for the reasons discussed above
MASK_LEFT_SHIFT = K.modifier_bit(K.LEFT_SHIFT)
MASK_RIGHT_SHIFT = K.modifier_bit(K.RIGHT_SHIFT)
MASK_ANY_SHIFT = (MASK_LEFT_SHIFT | MASK_RIGHT_SHIFT)

if POSITIONAL:
    keycodes = [
        K.BACKSPACE, K.ENTER, K.BACKSLASH, K.F8, K.F1, K.F2, K.F3, K_AT,
        K.THREE, K.W, K.A, K.FOUR, K.Z, K.S, K.E, K.LEFT_SHIFT,
        K.FIVE, K.R, K.D, K.SIX, K.C, K.F, K.T, K.X,
        K.SEVEN, K.Y, K.G, K.EIGHT, K.B, K.H, K.U, K.V,
        K.NINE, K.I, K.J, K.ZERO, K.M, K.K, K.O, K.N,
        K.DOWN_ARROW, K.P, K.L, K.UP_ARROW, K.PERIOD, K_COLON, K.MINUS, K.COMMA,
        K.LEFT_ARROW, K_ASTERISK, K.SEMICOLON, K.RIGHT_ARROW, K.ESCAPE, K.EQUALS, K_PLUS,
        K.FORWARD_SLASH, K.ONE, K_FN, K.LEFT_CONTROL, K.TWO, K.SPACE, K.ALT, K.Q, K.GRAVE_ACCENT,
    ]

    shifted = {
            K.TWO: (K.SHIFT, K.QUOTE),  # double quote
            K.SIX: (K.SHIFT, K.SEVEN),  # ampersand
            K.SEVEN: (K.QUOTE,),        # single quote
            K.EIGHT: (K.SHIFT, K.NINE), # left paren
            K.NINE: (K.SHIFT, K.ZERO),  # right paren
            K.ZERO: (K.SHIFT, K.SIX),  # caret
            K_AT: (K.SHIFT, K.LEFT_BRACKET),
            K_PLUS: (K.SHIFT, K.RIGHT_BRACKET),
            K_COLON: (K.LEFT_BRACKET,),
            K.SEMICOLON: (K.RIGHT_BRACKET,),
            K.EQUALS: (K.TAB,),
    }
else:
    # TODO clear/home, up/down positional arrows
    keycodes = [
        K.BACKSPACE, K.ENTER, K.LEFT_ARROW, K.F8, K.F1, K.F2, K.F3, K.LEFT_BRACKET,
        K.THREE, K.W, K.A, K.FOUR, K.Z, K.S, K.E, K.LEFT_SHIFT,
        K.FIVE, K.R, K.D, K.SIX, K.C, K.F, K.T, K.X,
        K.SEVEN, K.Y, K.G, K.EIGHT, K.B, K.H, K.U, K.V,
        K.NINE, K.I, K.J, K.ZERO, K.M, K.K, K.O, K.N,
        K.DOWN_ARROW, K.P, K.L, K.UP_ARROW, K.PERIOD, K.SEMICOLON, K.QUOTE, K.COMMA,
        K.BACKSLASH, K_ASTERISK, K.SEMICOLON, K.EQUALS, K.ESCAPE, K.RIGHT_ARROW, K.RIGHT_BRACKET,
        K.FORWARD_SLASH, K.ONE, K.HOME, K.LEFT_CONTROL, K.TWO, K.SPACE, K.ALT, K.Q, K.GRAVE_ACCENT,
    ]

    shifted = {
    }
class AsyncEventQueue:
    def __init__(self, events):
        self._events = events

    async def __await__(self):
        await asyncio.core._io_queue.queue_read(self._events)
        return self._events.get()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        pass

class XKROFilter:
    """Perform an X-key rollover algorithm, blocking ghosts if more than X keys are pressed at once

A key matrix without diodes can support 2-key rollover.
    """
    def __init__(self, rollover=2):
        self._count = 0
        self._rollover = rollover
        self._real = [0] * 64
        self._ghost = [0] * 64

    def __call__(self, event):
        self._ghost[event.key_number] = event.pressed
        if event.pressed:
            if self._count < self._rollover:
                self._real[event.key_number] = True
                yield event
            self._count += 1
        else:
            self._real[event.key_number] = False
            yield event
            self._count -= 1

twokey_filter = XKROFilter(2)

async def key_task():
    # Initialize Keyboard
    kbd = Keyboard(usb_hid.devices)

    with keypad.KeyMatrix(rows, cols) as keys, AsyncEventQueue(keys.events) as q:
        while True:
            ev = await q
            for ev in twokey_filter(ev):
                keycode = keycodes[ev.key_number]
                if callable(keycode):
                    keycode = keycode(ev)
                keycode = fn_state.fn_modify(keycode)
                if keycode is None:
                    continue
                old_report_modifier = kbd.report_modifier[0]
                shift_pressed = old_report_modifier & MASK_ANY_SHIFT
                if shift_pressed:
                    keycode = shifted.get(keycode, keycode)
                if isinstance(keycode, tuple):
                    if ev.pressed:
                        kbd.report_modifier[0] = old_report_modifier & ~MASK_ANY_SHIFT
                        kbd.press(*keycode)
                        kbd.release_all()
                        kbd.report_modifier[0] = old_report_modifier
                elif ev.pressed:
                    kbd.press(keycode)
                else:
                    kbd.release(keycode)


async def forever_task():
    while True:
        await asyncio.sleep(.1)

async def main():
    forever = asyncio.create_task(forever_task())
    key = asyncio.create_task(key_task())
    await asyncio.gather(  # Don't forget the await!
        forever,
        key,
    )

asyncio.run(main())
