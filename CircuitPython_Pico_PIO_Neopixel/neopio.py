# SPDX-FileCopyrightText: 2016 Damien P. George
# SPDX-FileCopyrightText: 2017 Scott Shawcroft for Adafruit Industries
# SPDX-FileCopyrightText: 2019 Carter Nelson
# SPDX-FileCopyrightText: 2019 Rose Hooper
# SPDX-FileCopyrightText: 2020 Jeff Epler
#
# SPDX-License-Identifier: MIT

"""
`neopio` - Neopixel strip driver using RP2040's PIO
===================================================

* Author(s): Damien P. George, Scott Shawcroft, Carter Nelson, Rose Hooper, Jeff Epler
"""

import adafruit_pioasm
import bitops
import microcontroller
import adafruit_pixelbuf
import rp2pio

_program = """
.program piopixl8
.side_set 2
;; out bit 1: '595 "ser"
;; side-set bit 1: '595 "srclk" (shift clock)
;; side-set bit 2: '595 "rclk" (latch clock)
;; 1 iteration = 2 cycles
;; 8 iterations + setup = 17 cycles
;; 1 loop = 51 cycles + 1 delay cycle = 52 cycles
;; 800kHz * 52 = 41.60MHz
;; 125MHz / 3 = 41.67MHz

.wrap_target
    set x, 7            side 2
    pull

bitloop0:
    set pins, 1         side 0
    jmp x--, bitloop0   side 1
    set x, 7            side 2
bitloop1:
    out pins, 1         side 0
    jmp x--, bitloop1   side 1
    set x, 7            side 2
bitloop2:
    set pins, 0         side 0
    jmp x--, bitloop2   side 1
.wrap
"""

_assembled = adafruit_pioasm.assemble(_program)

# Pixel color order constants
RGB = "RGB"
"""Red Green Blue"""
GRB = "GRB"
"""Green Red Blue"""
RGBW = "RGBW"
"""Red Green Blue White"""
GRBW = "GRBW"
"""Green Red Blue White"""

_gpio_order = [getattr(microcontroller.pin, f"GPIO{i}", None) for i in range(32)]

def _pin_directly_follows(a, b):
    if a not in _gpio_order or b not in _gpio_order:
        return False
    return _gpio_order.index(a) + 1 == _gpio_order.index(b)

class NeoPIO(adafruit_pixelbuf.PixelBuf):
    """
    A sequence of neopixels.

    :param ~microcontroller.Pin data: The shift-register's data pin
    :param ~microcontroller.Pin clock: The shift-register's clock pin.  Must directly follow data
    :param ~microcontroller.Pin strobe: The shift-register's strobe pi.  Must directly follow clock
    :param int n: The total number of neopixels.  Must be a multiple of the number of strands.
    :param int num_strands: The number of neopixels in each strand.
    :param int bpp: Bytes per pixel. 3 for RGB and 4 for RGBW pixels.
    :param float brightness: Brightness of the pixels between 0.0 and 1.0 where 1.0 is full
      brightness
    :param bool auto_write: True if the neopixels should immediately change when set. If False,
      `show` must be called explicitly.
    :param str pixel_order: Set the pixel color channel order. GRBW is set by default.

    Example for Raspberry Pi Pico:

    .. code-block:: python

        pixels = neopio.NeoPIO(board.GP0, board.GP1, board.GP2, 8*30, auto_write=False)
        pixels.fill(0xff0000)
        pixels.show()

    .. py:method:: NeoPIO.show()

        Shows the new colors on the pixels themselves if they haven't already
        been autowritten.

        The colors may or may not be showing after this function returns because
        it may be done asynchronously.

    .. py:method:: NeoPIO.fill(color)

        Colors all pixels the given ***color***.

    .. py:attribute:: brightness

        Overall brightness of the pixel (0 to 1.0)

    """

    def __init__(
        self, data, clock, strobe, n, *, num_strands=8, bpp=3, brightness=1.0,
        auto_write=True, pixel_order=None
    ):
        if not _pin_directly_follows(data, clock):
            raise ValueError("clock pin must directly follow data pin")
        if not _pin_directly_follows(clock, strobe):
            raise ValueError("strobe pin must directly follow clock pin")

        if n % num_strands:
            raise ValueError("Length must be a multiple of num_strands")
        if not pixel_order:
            pixel_order = GRB if bpp == 3 else GRBW
        else:
            if isinstance(pixel_order, tuple):
                order_list = [RGBW[order] for order in pixel_order]
                pixel_order = "".join(order_list)

        super().__init__(
            n, brightness=brightness, byteorder=pixel_order, auto_write=auto_write
        )

        self._transposed = bytearray(bpp*n*8//num_strands)
        self._num_strands = num_strands

        self._sm = rp2pio.StateMachine(
            _assembled,
            frequency=800_000 * 52,
            init=adafruit_pioasm.assemble("set pindirs 7"),
            first_out_pin=data,
            out_pin_count=1,
            first_set_pin=data,
            set_pin_count=3,
            first_sideset_pin=clock,
            sideset_pin_count=2,
            auto_pull=True,
            out_shift_right=False,
            pull_threshold=8,
        )


    def deinit(self):
        """Blank out the neopixels and release the state machine."""
        self.fill(0)
        self.show()
        self._sm.deinit()

    def __enter__(self):
        return self

    def __exit__(self, exception_type, exception_value, traceback):
        self.deinit()

    def __repr__(self):
        return "[" + ", ".join([str(x) for x in self]) + "]"

    @property
    def n(self):
        """
        The total number of neopixels in all strands (read-only)
        """
        return len(self)

    @property
    def num_strands(self):
        """
        The total number of neopixels in all strands (read-only)
        """
        return self._num_strands

    def _transmit(self, buffer):
        bitops.bit_transpose(buffer, self._transposed, self._num_strands)
        self._sm.write(self._transposed)
