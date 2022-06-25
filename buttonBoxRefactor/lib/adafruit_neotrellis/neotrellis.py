# SPDX-FileCopyrightText: 2018 Dean Miller for Adafruit Industries
#
# SPDX-License-Identifier: MIT

"""
``adafruit_neotrellis``
====================================================

4x4 elastomer buttons and RGB LEDs

* Author(s): Dean Miller

Implementation Notes
--------------------

**Hardware:**

**Software and Dependencies:**

* Adafruit CircuitPython firmware for the supported boards:
  https://github.com/adafruit/circuitpython/releases

* Adafruit Seesaw CircuitPython library
  https://github.com/adafruit/Adafruit_CircuitPython_seesaw/releases
"""

# imports

__version__ = "0.0.0-auto.0"
__repo__ = "https://github.com/adafruit/Adafruit_CircuitPython_neotrellis.git"

from time import sleep
from micropython import const
from adafruit_seesaw.keypad import Keypad, KeyEvent
from adafruit_seesaw.neopixel import NeoPixel

_NEO_TRELLIS_ADDR = const(0x2E)

_NEO_TRELLIS_NEOPIX_PIN = const(3)

_NEO_TRELLIS_NUM_ROWS = const(4)
_NEO_TRELLIS_NUM_COLS = const(4)
_NEO_TRELLIS_NUM_KEYS = const(16)

_NEO_TRELLIS_MAX_CALLBACKS = const(32)


def _key(xval):
    return int(int(xval / 4) * 8 + (xval % 4))


def _seesaw_key(xval):
    return int(int(xval / 8) * 4 + (xval % 8))


class NeoTrellis(Keypad):
    """Driver for the Adafruit NeoTrellis."""

    def __init__(self, i2c_bus, interrupt=False, addr=_NEO_TRELLIS_ADDR, drdy=None):
        super().__init__(i2c_bus, addr, drdy)
        self.interrupt_enabled = interrupt
        self.callbacks = [None] * _NEO_TRELLIS_NUM_KEYS
        self.pixels = NeoPixel(self, _NEO_TRELLIS_NEOPIX_PIN, _NEO_TRELLIS_NUM_KEYS)

    def activate_key(self, key, edge, enable=True):
        """Activate or deactivate a key on the trellis. Key is the key number from
        0 to 16. Edge specifies what edge to register an event on and can be
        NeoTrellis.EDGE_FALLING or NeoTrellis.EDGE_RISING. enable should be set
        to True if the event is to be enabled, or False if the event is to be
        disabled."""
        self.set_event(_key(key), edge, enable)

    def sync(self):
        """read any events from the Trellis hardware and call associated
        callbacks"""
        available = self.count
        sleep(0.0005)
        if available > 0:
            available = available + 2
            buf = self.read_keypad(available)
            for raw in buf:
                evt = KeyEvent(_seesaw_key((raw >> 2) & 0x3F), raw & 0x3)
                if (
                    evt.number < _NEO_TRELLIS_NUM_KEYS
                    and self.callbacks[evt.number] is not None
                ):
                    self.callbacks[evt.number](evt)
