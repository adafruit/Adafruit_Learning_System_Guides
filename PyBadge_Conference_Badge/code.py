# SPDX-FileCopyrightText: 2019 Melissa LeBlanc-Williams for Adafruit Industries
#
# SPDX-License-Identifier: MIT

"""
This is a Conference Badge type Name Tag that is intended to be displayed on
the PyBadge. Feel free to customize it to your heart's content.
"""

from math import sqrt, cos, sin, radians
import board
from micropython import const
import displayio
import neopixel
from keypad import ShiftRegisterKeys, Event
from adafruit_display_shapes.rect import Rect
from adafruit_display_text.label import Label
from adafruit_bitmap_font import bitmap_font

# Button Constants
BUTTON_LEFT = const(7)
BUTTON_UP = const(6)
BUTTON_DOWN = const(5)
BUTTON_RIGHT = const(4)
BUTTON_SEL = const(3)
BUTTON_START = const(2)
BUTTON_A = const(1)
BUTTON_B = const(0)

# Customizations
HELLO_STRING = "HELLO"
MY_NAME_STRING = "MY NAME IS"
NAME_STRING = "Blinka"
NAME_FONTNAME = "/fonts/Noto-18.bdf"
NEOPIXEL_COUNT = 5
BACKGROUND_COLOR = 0xFF0000
FOREGROUND_COLOR = 0xFFFFFF
BACKGROUND_TEXT_COLOR = 0xFFFFFF
FOREGROUND_TEXT_COLOR = 0x000000

settings = {"brightness": 0.2, "direction": 1, "speed": 1}

# Define the NeoPixel
neopixels = neopixel.NeoPixel(
    board.NEOPIXEL,
    NEOPIXEL_COUNT,
    brightness=settings["brightness"],
    auto_write=False,
    pixel_order=neopixel.GRB,
)

# Define Events and Shift Register
latest_event = Event()
last_event = Event()

pad = ShiftRegisterKeys(
    clock=board.BUTTON_CLOCK,
    data=board.BUTTON_OUT,
    latch=board.BUTTON_LATCH,
    key_count=8,
    value_when_pressed=True,
    interval=0.1,
    max_events=1,
)

# Make the Display Background
splash = displayio.Group()
board.DISPLAY.root_group = splash

color_bitmap = displayio.Bitmap(160, 128, 1)
color_palette = displayio.Palette(1)
color_palette[0] = BACKGROUND_COLOR

bg_sprite = displayio.TileGrid(color_bitmap, pixel_shader=color_palette, x=0, y=0)
splash.append(bg_sprite)

# Draw a Foreground Rectangle where the name goes
rect = Rect(0, 50, 160, 70, fill=FOREGROUND_COLOR)
splash.append(rect)

# Load the Hello font
large_font_name = "/fonts/Verdana-Bold-18.bdf"
large_font = bitmap_font.load_font(large_font_name)
large_font.load_glyphs(HELLO_STRING.encode("utf-8"))

# Load the "My Name Is" font
small_font_name = "/fonts/Arial-12.bdf"
small_font = bitmap_font.load_font(small_font_name)
small_font.load_glyphs(MY_NAME_STRING.encode("utf-8"))

# Load the Name font
name_font_name = NAME_FONTNAME
name_font = bitmap_font.load_font(name_font_name)
name_font.load_glyphs(NAME_STRING.encode("utf-8"))

# Setup and Center the Hello Label
splash.append(
    Label(
        large_font,
        anchor_point=(0.5, 0.5),
        anchored_position=(board.DISPLAY.width // 2, 15),
        text=HELLO_STRING,
        color=BACKGROUND_TEXT_COLOR,
    )
)

# Setup and Center the "My Name Is" Label
splash.append(
    Label(
        small_font,
        anchor_point=(0.5, 0.5),
        anchored_position=(board.DISPLAY.width // 2, 35),
        text=MY_NAME_STRING,
        color=BACKGROUND_TEXT_COLOR,
    )
)

# Setup and Center the Name Label
splash.append(
    Label(
        name_font,
        anchor_point=(0.5, 0.5),
        anchored_position=(board.DISPLAY.width // 2, 85),
        text=NAME_STRING,
        color=FOREGROUND_TEXT_COLOR,
    )
)

# Remap the calculated rotation to 0 - 255
def remap(vector):
    return int(((255 * vector + 85) * 0.75) + 0.5)


# Calculate the Hue rotation starting with Red as 0 degrees
def rotate(degrees):
    cosA = cos(radians(degrees))
    sinA = sin(radians(degrees))
    red = cosA + (1.0 - cosA) / 3.0
    green = 1.0 / 3.0 * (1.0 - cosA) + sqrt(1.0 / 3.0) * sinA
    blue = 1.0 / 3.0 * (1.0 - cosA) - sqrt(1.0 / 3.0) * sinA
    return (remap(red), remap(green), remap(blue))


palette = []
pixels = []

# Generate a rainbow palette
for degree in range(0, 360):
    color = rotate(degree)
    palette.append(color[0] << 16 | color[1] << 8 | color[2])

# Create the Pattern
for x in range(0, NEOPIXEL_COUNT):
    pixels.append(x * 360 // NEOPIXEL_COUNT)


def check_buttons(event):
    if event.key_number == BUTTON_RIGHT:
        settings["direction"] = -1
    elif event.key_number == BUTTON_LEFT:
        settings["direction"] = 1
    elif (event.key_number == BUTTON_UP) and settings["speed"] < 10:
        settings["speed"] += 1
    elif (event.key_number == BUTTON_DOWN) and settings["speed"] > 1:
        settings["speed"] -= 1
    elif (event.key_number == BUTTON_A) and settings["brightness"] < 0.5:
        settings["brightness"] += 0.025
    elif (event.key_number == BUTTON_B) and settings["brightness"] > 0.025:
        settings["brightness"] -= 0.025


# Main Loop
last_read = 0
while True:
    for color in range(0, 360, settings["speed"]):
        for index in range(0, NEOPIXEL_COUNT):
            palette_index = pixels[index] + color * settings["direction"]
            if palette_index >= 360:
                palette_index -= 360
            elif palette_index < 0:
                palette_index += 360
            neopixels[index] = palette[palette_index]
        neopixels.show()
        neopixels.brightness = settings["brightness"]
        pad.events.get_into(latest_event)
        if latest_event.pressed and latest_event.key_number != last_event.key_number:
            check_buttons(latest_event)
            last_event = latest_event
            latest_event = Event(
                key_number=8
            )  # An imaginary key number that doesn't exist!
