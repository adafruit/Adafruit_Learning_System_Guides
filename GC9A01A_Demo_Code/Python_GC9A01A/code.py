# SPDX-FileCopyrightText: 2025 Liz Clark for Adafruit Industries
# SPDX-FileCopyrightText: Adapted from Melissa LeBlanc-Williams's Pi Demo Code
#
# SPDX-License-Identifier: MIT

'''Raspberry Pi Graphics example for the 240x240 Round TFT'''

import time
import digitalio
import board
from PIL import Image, ImageDraw, ImageFont
from adafruit_rgb_display import gc9a01a

BORDER = 20
FONTSIZE = 24

cs_pin = digitalio.DigitalInOut(board.CE0)
dc_pin = digitalio.DigitalInOut(board.D25)
reset_pin = digitalio.DigitalInOut(board.D27)

BAUDRATE = 24000000

spi = board.SPI()

disp = gc9a01a.GC9A01A(spi, rotation=180,
    width=135, height=240,
    x_offset=53, y_offset=40,
    cs=cs_pin,
    dc=dc_pin,
    rst=reset_pin,
    baudrate=BAUDRATE,
)

width = disp.width
height = disp.height

# -------TEXT AND SHAPES---------
image1 = Image.new("RGB", (width, height))
draw1 = ImageDraw.Draw(image1)
draw1.rectangle((0, 0, width, height), fill=(0, 255, 0))  # Green background

draw1.rectangle(
    (BORDER, BORDER, width - BORDER - 1, height - BORDER - 1), fill=(170, 0, 136)
)
font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", FONTSIZE)
text = "Hello\nWorld!"
(font_width, font_height) = font.getsize(text)
draw1.text(
    (30, height // 2 - font_height // 2-12),
    text,
    font=font,
    fill=(255, 255, 0),
)

# ------BLINKA JPEG DISPLAY----------
image2 = Image.open("blinka_round.jpg")
image_ratio = image2.width / image2.height
screen_ratio = width / height
scaled_width = width
scaled_height = image2.height * width // image2.width
image2 = image2.resize((scaled_width, scaled_height), Image.BICUBIC)
x = scaled_width // 2 - width // 2
y = scaled_height // 2 - height // 2
image2 = image2.crop((x, y, x + width, y + height))

while True:
    disp.image(image1)  # show text
    time.sleep(2)
    disp.image(image2)  # show blinka
    time.sleep(2)
