# SPDX-FileCopyrightText: 2021 ladyada for Adafruit Industries
# SPDX-License-Identifier: MIT
"""Blinka EPD Demo for the Quad Color eInk"""
import board
import digitalio
from PIL import Image, ImageDraw, ImageFont

from adafruit_epd.epd import Adafruit_EPD
from adafruit_epd.jd79661 import Adafruit_JD79661

# create the spi device and pins we will need
spi = board.SPI()
ecs = digitalio.DigitalInOut(board.CE0)
dc = digitalio.DigitalInOut(board.D25)
srcs = None
rst = digitalio.DigitalInOut(board.D27)  # can be None to not use this pin
busy = digitalio.DigitalInOut(board.D17)  # can be None to not use this pin

display = Adafruit_JD79661(122, 250, spi,
                          cs_pin=ecs, dc_pin=dc, sramcs_pin=srcs,
                          rst_pin=rst, busy_pin=busy)

display.rotation = 3
width = display.width
height = display.height
image = Image.new("RGB", (width, height))

WHITE = (0xFF, 0xFF, 0xFF)
YELLOW = (0xFF, 0xFF, 0x00)
RED = (0xFF, 0x00, 0x00)
BLACK = (0x00, 0x00, 0x00)

# clear the buffer
display.fill(Adafruit_EPD.WHITE)

# Get drawing object to draw on image.
draw = ImageDraw.Draw(image)
# empty it
draw.rectangle((0, 0, width, height), fill=WHITE)

# Draw an outline box
draw.rectangle((1, 1, width - 2, height - 2), outline=BLACK, fill=WHITE)

# Draw some shapes.
# First define some constants to allow easy resizing of shapes.
padding = 5
shape_width = 30
top = padding
bottom = height - padding
# Move left to right keeping track of the current x position for drawing shapes.
x = padding
# Draw an ellipse.
draw.ellipse((x, top, x + shape_width, bottom), outline=YELLOW, fill=WHITE)
x += shape_width + padding
# Draw a rectangle.
draw.rectangle((x, top, x + shape_width, bottom), outline=RED, fill=BLACK)
x += shape_width + padding
# Draw a triangle.
draw.polygon(
    [(x, bottom), (x + shape_width / 2, top), (x + shape_width, bottom)],
    outline=BLACK,
    fill=RED,
)
x += shape_width + padding
# Draw an X.
draw.line((x, bottom, x + shape_width, top), fill=YELLOW)
draw.line((x, top, x + shape_width, bottom), fill=YELLOW)
x += shape_width + padding

# Load default font.
font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 20)

draw.text((x, top), "Hello", font=font, fill=YELLOW)
draw.text((x, top + 20), "World!", font=font, fill=YELLOW)

# Display image.
display.image(image)

display.display()
