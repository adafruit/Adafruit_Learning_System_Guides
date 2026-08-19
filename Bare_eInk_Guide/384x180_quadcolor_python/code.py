# SPDX-FileCopyrightText: 2019 Melissa LeBlanc-Williams for Adafruit Industries
# SPDX-License-Identifier: MIT

"""
ePaper Display Shapes and Text demo using the Pillow Library.
3.52" Quad Color 384x180 display
https://www.adafruit.com/product/6414
"""

import board
import busio
import digitalio
from PIL import Image, ImageDraw, ImageFont

from adafruit_epd.jd79667 import Adafruit_JD79667

# RGB colors
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
RED = (255, 0, 0)
YELLOW = (255, 255, 0)

# Create the SPI device and pins
spi = busio.SPI(board.SCK, MOSI=board.MOSI, MISO=board.MISO)
ecs = digitalio.DigitalInOut(board.CE0)
dc = digitalio.DigitalInOut(board.D22)
srcs = None  # No SRAM
rst = digitalio.DigitalInOut(board.D27)
busy = digitalio.DigitalInOut(board.D17)

display = Adafruit_JD79667(
    180,
    384,
    spi,
    cs_pin=ecs,
    dc_pin=dc,
    sramcs_pin=srcs,
    rst_pin=rst,
    busy_pin=busy,
)

display.rotation = 3

# Get display dimensions
width = display.width
height = display.height
image = Image.new("RGB", (width, height))
# Get drawing object
draw = ImageDraw.Draw(image)

# Fill background with white
draw.rectangle((0, 0, width, height), fill=WHITE)

# Draw a border
draw.rectangle((0, 0, width - 1, height - 1), outline=BLACK, fill=WHITE)

# Draw some shapes to demonstrate all four colors
padding = 10
shape_width = 30
top = padding + 10
bottom = height - padding - 10

# Starting x position
x = padding + 10

# Draw an ellipse filled with red
draw.ellipse((x, top, x + shape_width, bottom), outline=RED, fill=None)
x += shape_width + padding

# Draw a rectangle filled with yellow
draw.rectangle((x, top, x + shape_width, bottom), outline=YELLOW, fill=BLACK)
x += shape_width + padding

# Draw a triangle filled with red
draw.polygon(
    [(x, bottom), (x + shape_width / 2, top), (x + shape_width, bottom)],
    outline=BLACK,
    fill=YELLOW,
)
x += shape_width + padding

# Draw an X with red and yellow lines
draw.line((x, bottom, x + shape_width, top), fill=RED)
draw.line((x, top, x + shape_width, bottom), fill=BLACK)
x += shape_width + padding

# Add some text
font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 28)

# Draw text in different colors
draw.text((x, top), "Hello", font=font, fill=BLACK)
draw.text((x, top + 28), "World!", font=font, fill=RED)
draw.text((x, top + (28*2)), "Quad", font=font, fill=YELLOW)
draw.text((x, top + (28*3)), "Color!", font=font, fill=BLACK)

display.image(image)

display.display()
