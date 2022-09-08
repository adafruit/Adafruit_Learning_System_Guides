# SPDX-FileCopyrightText: 2022 Jeff Epler for Adafruit Industries
# SPDX-License-Identifier: MIT

# KeyMatrix Whisperer
#
# Interactively determine a matrix keypad's row and column pins
#
# Wait until the program prints "press keys now". Then, press and hold a key
# until it registers. Repeat until all rows and columns are identified. If your
# keyboard matrix does NOT have dioes, you MUST take care to only press a
# single key at a time.
#
# How identification is performed: When a key is pressed _some_ pair of I/Os
# will be connected. This code repeatedly scans all possible pairs, recording
# them.  The very first pass when no key is pressed is recorded as "junk" so it
# can be ignored.
#
# Then, the first I/O involved in the first non-junk press is arbitrarily
# recorded as a "row pin". If the matrix does not have diodes, this can
# actually vary from run to run or depending on the first key you pressed. The
# only net effect of this is that the row & column lists are exchanged.
#
# After enough key presses, you'll get a full list of "row" and "column" pins.
# For instance, on the Commodore 16 keyboard you'd get 8 row pins and 8 column pins.
#
# This doesn't help determine the LOGICAL ORDER of rows and columns or the
# physical layout of the keyboard. You still have to do that for yourself.

import board
import microcontroller
from digitalio import DigitalInOut, Pull

# List of pins to test, or None to test all pins
IO_PINS = None # [board.D0, board.D1]
# Which value(s) to set the driving pin to
values = [True] # [True, False]

def discover_io():
    return [pin_maybe for name in dir(microcontroller.pin)
            if isinstance(pin_maybe := getattr(microcontroller.pin, name), microcontroller.Pin)]

def pin_lookup(pin):
    for i in dir(board):
        if getattr(board, i) is pin:
            return i
    for i in dir(microcontroller.pin):
        if getattr(microcontroller.pin, i) is pin:
            return i
    return str(pin)

# Find all I/O pins, if IO_PINS is not explicitly set above
if IO_PINS is None:
    IO_PINS = discover_io()

# Initialize all pins as inputs, make a lookup table to get the name from the pin
ios_lookup = dict([(pin_lookup(pin), DigitalInOut(pin)) for pin in IO_PINS]) # pylint: disable=consider-using-dict-comprehension
ios = ios_lookup.values()
ios_items = ios_lookup.items()
for io in ios:
    io.switch_to_input(pull=Pull.UP)

# Partial implementation of 'defaultdict' class from standard Python from
# https://github.com/micropython/micropython-lib/blob/master/python-stdlib/collections.defaultdict/collections/defaultdict.py
class defaultdict:
    @staticmethod
    def __new__(cls, default_factory=None, **kwargs): # pylint: disable=unused-argument
        # Some code (e.g. urllib.urlparse) expects that basic defaultdict
        # functionality will be available to subclasses without them
        # calling __init__().
        self = super(defaultdict, cls).__new__(cls)
        self.d = {}
        return self

    def __init__(self, default_factory=None, **kwargs):
        self.d = kwargs
        self.default_factory = default_factory

    def __getitem__(self, key):
        try:
            return self.d[key]
        except KeyError:
            v = self.__missing__(key)
            self.d[key] = v
            return v

    def __setitem__(self, key, v):
        self.d[key] = v

    def __delitem__(self, key):
        del self.d[key]

    def __contains__(self, key):
        return key in self.d

    def __missing__(self, key):
        if self.default_factory is None:
            raise KeyError(key)
        return self.default_factory()

# Track combinations that were pressed, including ones during the "junk" scan
pressed_or_junk = defaultdict(set)
# Track combinations that were pressed, excluding the "junk" scan
pressed = defaultdict(set)
# During the first run, anything scanned is "junk". Could occur for unused pins.
first_run = True
# List of pins identified as rows and columns
rows = []
cols = []
# The first pin identified is arbitrarily called a 'row' pin.
row_arbitrarily = None

while True:
    changed = False
    last_pressed = None
    for value in values:
        pull = [Pull.UP, Pull.DOWN][value]
        for io in ios:
            io.switch_to_input(pull=pull)
        for name1, io1 in ios_items:
            io1.switch_to_output(value)
            for name2, io2 in ios_items:
                if io2 is io1:
                    continue
                if io2.value == value:
                    if first_run:
                        pressed_or_junk[name1].add(name2)
                        pressed_or_junk[name2].add(name1)
                    elif name2 not in pressed_or_junk[name1]:
                        if row_arbitrarily is None:
                            row_arbitrarily = name1
                        pressed_or_junk[name1].add(name2)
                        pressed_or_junk[name2].add(name1)
                        if name2 not in pressed[name1]:
                            pressed[name1].add(name2)
                            pressed[name2].add(name1)
                            changed = True
                    if name2 in pressed[name1]:
                        last_pressed = (name1, name2)
                        print("Key registered. Release to continue")
                        while io2.value == value:
                            pass
            io1.switch_to_input(pull=pull)
    if first_run:
        print("Press keys now")
        first_run = False
    elif changed:
        rows = set([row_arbitrarily])
        cols = set()
        to_check = [row_arbitrarily]
        for check in to_check:
            for other in pressed[check]:
                if other in rows or other in cols:
                    continue
                if check in rows:
                    cols.add(other)
                else:
                    rows.add(other)
                to_check.append(other) # pylint: disable=modified-iterating-list

        rows = sorted(rows)
        cols = sorted(cols)
    if changed or last_pressed:
        print("Rows", len(rows), *rows)
        print("Cols", len(cols), *cols)
        print("Last pressed", *last_pressed)
        print()
