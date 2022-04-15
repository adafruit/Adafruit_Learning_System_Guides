# SPDX-FileCopyrightText: 2022 Phillip Burgess for Adafruit Industries
#
# SPDX-License-Identifier: MIT

"""
Base class for Little Connection Machine projects. Allows drawing on a
single PIL image spanning eight IS31fl3731 Charlieplex matrices and handles
double-buffered updates. Matrices are arranged four across, two down, "the
tall way" (9 pixels across, 16 down) with I2C pins at the bottom.

IS31fl3731 can be jumpered for one of four addresses. Because this uses
eight, two groups are split across a pair of "soft" I2C buses by adding this
to /boot/config.txt:
dtoverlay=i2c-gpio,bus=2,i2c_gpio_scl=17,i2c_gpio_sda=27,i2c_gpio_delay_us=1
dtoverlay=i2c-gpio,bus=3,i2c_gpio_scl=23,i2c_gpio_sda=24,i2c_gpio_delay_us=1
And run:
pip3 install adafruit-extended-bus adafruit-circuitpython-is31fl3731
The extra buses will be /dev/i2c-2 and /dev/i2c-3. These are not as fast as
the "true" I2C bus, but are adequate for this application.
"""

import argparse
import signal
import sys
from PIL import Image
from PIL import ImageDraw
from adafruit_extended_bus import ExtendedI2C as I2C
from adafruit_is31fl3731.matrix import Matrix as Display

DEFAULT_BRIGHTNESS = 40


class CM1:
    """A base class for Little Connection Machine projects, handling common
    functionality like LED matrix init, updates and signal handler."""

    # pylint: disable=unused-argument
    def __init__(self, *args, **kwargs):
        self.brightness = DEFAULT_BRIGHTNESS

        parser = argparse.ArgumentParser()
        parser.add_argument(
            "-b",
            action="store",
            help="Brightness, 0-255. Default: %d" % DEFAULT_BRIGHTNESS,
            default=42,
            type=int,
        )
        args = parser.parse_args()
        if args.b:
            self.brightness = min(max(args.b, 0), 255)

        i2c = [
            I2C(2),  # Extended bus on 17, 27 (clock, data)
            I2C(3),  # Extended bus on 23, 24 (clock, data)
        ]
        self.display = [
            Display(i2c[0], address=0x74, frames=(0, 1)),  # Upper row
            Display(i2c[0], address=0x75, frames=(0, 1)),
            Display(i2c[0], address=0x76, frames=(0, 1)),
            Display(i2c[0], address=0x77, frames=(0, 1)),
            Display(i2c[1], address=0x74, frames=(0, 1)),  # Lower row
            Display(i2c[1], address=0x75, frames=(0, 1)),
            Display(i2c[1], address=0x76, frames=(0, 1)),
            Display(i2c[1], address=0x77, frames=(0, 1)),
        ]
        self.image = Image.new("L", (9 * 4, 16 * 2))
        self.draw = ImageDraw.Draw(self.image)
        self.frame_index = 0  # Front/back buffer index
        signal.signal(signal.SIGTERM, self.signal_handler)  # Kill signal

    def run(self):
        """Placeholder. Override this in subclass."""

    # pylint: disable=unused-argument
    def signal_handler(self, signum, frame):
        """Signal handler. Clears all matrices and exits."""
        self.clear()
        self.redraw()
        sys.exit(0)

    def clear(self):
        """Clears PIL image. Does not invoke refresh(), just clears."""
        self.draw.rectangle([0, 0, self.image.size[0], self.image.size[1]], fill=0)

    def redraw(self):
        """Update matrices with PIL image contents, swap buffers."""
        # First pass crops out sections over the overall image, rotates
        # them to matrix space, and writes this data to each matrix.
        for num, display in enumerate(self.display):
            col = (num % 4) * 9
            row = (num // 4) * 16
            cropped = self.image.crop((col, row, col + 9, row + 16))
            cropped = cropped.rotate(angle=-90, expand=1)
            display.image(cropped, frame=self.frame_index)
        # Swapping frames is done in a separate pass so they all occur
        # close together, no conspicuous per-matrix refresh.
        for display in self.display:
            display.frame(self.frame_index, show=True)  # True = show frame
        self.frame_index ^= 1  # Swap frame index

    def process(self):
        """Call CM1 subclass run() function, with keyboard interrupt trapping
        centralized here so it doesn't need to be implemented everywhere."""
        try:
            self.run()  # In subclass
        except KeyboardInterrupt:
            self.signal_handler(0, 0)  # clear/redraw/exit
