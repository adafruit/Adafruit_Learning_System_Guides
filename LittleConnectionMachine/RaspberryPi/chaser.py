# SPDX-FileCopyrightText: 2022 Phillip Burgess for Adafruit Industries
#
# SPDX-License-Identifier: MIT

"""
Chaser lights for Little Connection Machine. Random bit patterns shift
left or right in groups of four rows. Nothing functional, just looks cool.
Inspired by Jurassic Park's blinky CM-5 prop. As it's a self-contained demo
and not connected to any system services or optional installations, this is
the simplest of the Little Connection Machine examples, making it a good
starting point for your own projects...there's the least to rip out here!
"""

import random
import time
from cm1 import CM1

DENSITY = 30  # Percentage of bits to set (0-100)
FPS = 6  # Frames/second to update (roughly)


def randbit(bitpos):
    """Return a random bit value based on the global DENSITY percentage,
    shifted into position 'bitpos' (typically 0 or 8 for this code)."""
    return (random.randint(1, 100) > (100 - DENSITY)) << bitpos


class Chaser(CM1):
    """Purely decorative chaser lights for Little Connection Machine."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)  # CM1 base initialization
        # Initialize all bits to 0. 32 rows, 4 columns of 9-bit patterns.
        self.bits = [[0 for _ in range(4)] for _ in range(32)]

    def run(self):
        """Main loop for Little Connection Machine chaser lights."""

        last_redraw_time = time.monotonic()
        interval = 1 / FPS  # Frame-to-frame time

        while True:
            self.clear()  # Clear PIL self.image, part of the CM1 base class
            for row in range(self.image.height):  # For each row...
                for col in range(4):  # For each of 4 columns...
                    # Rows operate in groups of 4. Some shift left, others
                    # shift right. Empty spots are filled w/random bits.
                    if row & 4:
                        self.bits[row][col] = (self.bits[row][col] >> 1) + randbit(8)
                    else:
                        self.bits[row][col] = (self.bits[row][col] << 1) + randbit(0)
                    # Draw new bit pattern into image...
                    xoffset = col * 9
                    for bit in range(9):
                        mask = 0x100 >> bit
                        if self.bits[row][col] & mask:
                            # self.draw is PIL draw object in CM1 base class
                            self.draw.point([xoffset + bit, row], fill=self.brightness)

            # Dillydally to roughly frames/second refresh. Preferable to
            # time.sleep() because bit-drawing above isn't deterministic.
            while (time.monotonic() - last_redraw_time) < interval:
                pass
            last_redraw_time = time.monotonic()
            self.redraw()


if __name__ == "__main__":
    MY_APP = Chaser()  # Instantiate class, calls __init__() above
    MY_APP.process()
