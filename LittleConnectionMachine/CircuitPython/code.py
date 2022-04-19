# SPDX-FileCopyrightText: 2022 Phillip Burgess for Adafruit Industries
#
# SPDX-License-Identifier: MIT

"""
CircuitPython random blinkenlights for Little Connection Machine. For
Raspberry Pi Pico RP2040, but could be adapted to other CircuitPython-
capable boards with two or more I2C buses. Requires adafruit_bus_device
and adafruit_is31fl3731 libraries.

This code plays dirty pool to get fast matrix updates and is NOT good code
to learn from, and might fail to work with future versions of the IS31FL3731
library. But doing things The Polite Way wasn't fast enough. Explained as
we go...
"""

# pylint: disable=import-error
import random
import board
import busio
from adafruit_is31fl3731.matrix import Matrix as Display

BRIGHTNESS = 40  # CONFIGURABLE: LED brightness, 0 (off) to 255 (max)
PERCENT = 33  # CONFIGURABLE: amount of 'on' LEDs, 0 (none) to 100 (all)

# This code was originally written for the Raspberry Pi Pico, but should be
# portable to any CircuitPython-capable board WITH TWO OR MORE I2C BUSES.
# IS31FL3731 can have one of four addresses, so to run eight of them we
# need *two* I2C buses, and not all boards can provide that. Here's where
# you'd define the pin numbers for a board...
I2C1_SDA = board.GP18  # First I2C bus
I2C1_SCL = board.GP19
I2C2_SDA = board.GP16  # Second I2C bus
I2C2_SCL = board.GP17

# pylint: disable=too-few-public-methods
class FakePILImage:
    """Minimal class meant to simulate a small subset of a Python PIL image,
    so we can pass it to the IS31FL3731 image() function later. THIS IS THE
    DIRTY POOL PART OF THE CODE, because CircuitPython doesn't have PIL,
    it's too much to handle. That image() function is normally meant for
    robust "desktop" Python, using the Blinka package...but it's still
    present (but normally goes unused) in CircuitPython. Having worked with
    that library source, I know exactly what object members its looking for,
    and can fake a minimal set here...BUT THIS MAY BREAK IF THE LIBRARY OR
    PIL CHANGES!"""

    def __init__(self):
        self.mode = "L"  # Grayscale mode in PIL
        self.size = (16, 9)  # 16x9 pixels
        self.pixels = bytearray(16 * 9)  # Pixel buffer

    def tobytes(self):
        """IS31 lib requests image pixels this way, more dirty pool."""
        return self.pixels


# Okay, back to business...
# Instantiate the two I2C buses. 400 KHz bus speed is recommended.
# Default 100 KHz is a bit slow, and 1 MHz has occasional glitches.
I2C = [
    busio.I2C(I2C1_SCL, I2C1_SDA, frequency=400000),
    busio.I2C(I2C2_SCL, I2C2_SDA, frequency=400000),
]
# Four matrices on each bus, for a total of eight...
DISPLAY = [
    Display(I2C[0], address=0x74, frames=(0, 1)),  # Upper row
    Display(I2C[0], address=0x75, frames=(0, 1)),
    Display(I2C[0], address=0x76, frames=(0, 1)),
    Display(I2C[0], address=0x77, frames=(0, 1)),
    Display(I2C[1], address=0x74, frames=(0, 1)),  # Lower row
    Display(I2C[1], address=0x75, frames=(0, 1)),
    Display(I2C[1], address=0x76, frames=(0, 1)),
    Display(I2C[1], address=0x77, frames=(0, 1)),
]

IMAGE = FakePILImage()  # Instantiate fake PIL image object
FRAME_INDEX = 0  # Double-buffering frame index

while True:
    # Draw to each display's "back" frame buffer
    for disp in DISPLAY:
        for pixel in range(0, 16 * 9):  # Randomize each pixel
            IMAGE.pixels[pixel] = BRIGHTNESS if random.randint(1, 100) <= PERCENT else 0
        # Here's the function that we're NOT supposed to call in
        # CircuitPython, but is still present. This writes the pixel
        # data to the display's back buffer. Pass along our "fake" PIL
        # image and it accepts it.
        disp.image(IMAGE, frame=FRAME_INDEX)

    # Then quickly flip all matrix display buffers to FRAME_INDEX
    for disp in DISPLAY:
        disp.frame(FRAME_INDEX, show=True)
    FRAME_INDEX ^= 1  # Swap buffers


# This is actually the LESS annoying way to get fast updates. Other involved
# writing IS31 registers directly and accessing intended-as-private methods
# in the IS31 lib. That's a really bad look. It's pretty simple here because
# this code is just drawing random dots. Producing a spatially-coherent
# image would take a lot more work, because matrices are rotated, etc.
# The PIL+Blinka code for Raspberry Pi easily handles such things, so
# consider working with that if you need anything more sophisticated.
