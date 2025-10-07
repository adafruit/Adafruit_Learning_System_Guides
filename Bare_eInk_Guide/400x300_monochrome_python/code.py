# SPDX-FileCopyrightText: 2019 Melissa LeBlanc-Williams for Adafruit Industries
# SPDX-License-Identifier: MIT

"""
ePaper Display Shapes and Text demo using the Pillow Library.
4.2" 300x400 Monochrome
https://www.adafruit.com/product/6381
"""

import board
import busio
import digitalio
from PIL import Image, ImageDraw, ImageFont

from adafruit_epd.ssd1683 import Adafruit_SSD1683

# First define some color constants
WHITE = (0xFF, 0xFF, 0xFF)
BLACK = (0xFF, 0x00, 0x00)

# Next define some constants to allow easy resizing of shapes and colors
BORDER = 20
FONTSIZE = 24
BACKGROUND_COLOR = BLACK
FOREGROUND_COLOR = WHITE
TEXT_COLOR = BLACK

# create the spi device and pins we will need
spi = busio.SPI(board.SCK, MOSI=board.MOSI, MISO=board.MISO)
ecs = digitalio.DigitalInOut(board.CE0)
dc = digitalio.DigitalInOut(board.D22)
srcs = None
rst = digitalio.DigitalInOut(board.D27)
busy = digitalio.DigitalInOut(board.D17)


display = Adafruit_SSD1683(400, 300,        # 4.2" 300x400 monochrome display
    spi,
    cs_pin=ecs,
    dc_pin=dc,
    sramcs_pin=srcs,
    rst_pin=rst,
    busy_pin=busy,
)

display.rotation = 0
width = display.width
height = display.height
image = Image.new("RGB", (width, height))

# clear the buffer
display.fill(WHITE)

# Get drawing object to draw on image.
draw = ImageDraw.Draw(image)
# empty it
draw.rectangle((0, 0, width, height), fill=WHITE)

# Draw an outline box
draw.rectangle((1, 1, width - 2, height - 2), outline=BLACK, fill=WHITE)

# Draw some shapes.
# First define some constants to allow easy resizing of shapes.
padding = 15
shape_width = 50 
top = padding
bottom = height - padding
# Move left to right keeping track of the current x position for drawing shapes.
x = padding
# Draw an ellipse.
draw.ellipse((x, top, x + shape_width, bottom), outline=BLACK, fill=WHITE)
x += shape_width + padding
# Draw a rectangle.
draw.rectangle((x, top, x + shape_width, bottom), outline=BLACK, fill=BLACK)
x += shape_width + padding
# Draw a triangle.
draw.polygon(
    [(x, bottom), (x + shape_width / 2, top), (x + shape_width, bottom)],
    outline=BLACK,
    fill=BLACK,
)
x += shape_width + padding
# Draw an X.
draw.line((x, bottom, x + shape_width, top), fill=BLACK)
draw.line((x, top, x + shape_width, bottom), fill=BLACK)
x += shape_width + padding

# Load default font.
font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 30)

draw.text((x, top), "Hello", font=font, fill=BLACK)
draw.text((x, top + 30), "World!", font=font, fill=BLACK)

# Display image.
display.image(image)

display.display()
