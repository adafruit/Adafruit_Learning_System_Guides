# SPDX-FileCopyrightText: 2019 Melissa LeBlanc-Williams for Adafruit Industries
# SPDX-License-Identifier: MIT
"""
Image resizing and drawing using the Pillow Library for Quad Color eInk
"""
import board
import digitalio
from PIL import Image, ImageEnhance
from adafruit_epd.jd79661 import Adafruit_JD79661

# create the spi device and pins we will need
spi = board.SPI()
ecs = digitalio.DigitalInOut(board.CE0)
dc = digitalio.DigitalInOut(board.D25)
srcs = None
rst = digitalio.DigitalInOut(board.D27)  # can be None to not use this pin
busy = digitalio.DigitalInOut(board.D17)  # can be None to not use this pin

# give them all to our driver
display = Adafruit_JD79661(122, 250,        # 2.13" Quad-color display
    spi,
    cs_pin=ecs,
    dc_pin=dc,
    sramcs_pin=srcs,
    rst_pin=rst,
    busy_pin=busy,
)
display.rotation = 3

image = Image.open("blinka.png")

# Scale the image to the smaller screen dimension
image_ratio = image.width / image.height
screen_ratio = display.width / display.height
if screen_ratio < image_ratio:
    scaled_width = image.width * display.height // image.height
    scaled_height = display.height
else:
    scaled_width = display.width
    scaled_height = image.height * display.width // image.width
image = image.resize((scaled_width, scaled_height), Image.BICUBIC)

# Crop and center the image
x = scaled_width // 2 - display.width // 2
y = scaled_height // 2 - display.height // 2
image = image.crop((x, y, x + display.width, y + display.height)).convert("RGB")

quad_colors = [
    (0, 0, 0),        # Black
    (255, 255, 255),  # White
    (255, 0, 0),      # Red
    (255, 255, 0),    # Yellow
]
palette_image = Image.new('P', (1, 1))

# Create palette data - PIL expects 768 values (256 colors * 3 channels)
palette_data = []
for color in quad_colors:
    palette_data.extend(color)
# Fill remaining palette entries with black
for i in range(4, 256):
    palette_data.extend([0, 0, 0])

palette_image.putpalette(palette_data)

enhancer = ImageEnhance.Color(image)
image = enhancer.enhance(1.5)

temp_image = image.quantize(palette=palette_image, dither=Image.Dither.FLOYDSTEINBERG)

pixels = temp_image.load()
width, height = temp_image.size

final_palette = Image.new('P', (1, 1))
final_palette.putpalette(palette_data)
final_image = Image.new('P', (width, height))
final_pixels = final_image.load()

# Copy pixels, ensuring they use indices 0-3
for y in range(height):
    for x in range(width):
        # Clamp pixel values to 0-3 range
        final_pixels[x, y] = min(pixels[x, y], 3)

final_image.putpalette(palette_data)

# Convert back to RGB for display
image = final_image.convert('RGB')

# Display image.
display.image(image)
display.display()
