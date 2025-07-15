# SPDX-FileCopyrightText: Copyright (c) 2025 Tim C for Adafruit Industries
# SPDX-FileCopyrightText: Copyright (c) 2025 Anne Barela for Adafruit Industries
#
# SPDX-License-Identifier: MIT
#
# Make an adafruit_color_terminal terminal with ASCI escape character support
# This uses a Code Page 437 LVGL font to draw a box also
#
import gc
import supervisor
import displayio
from lvfontio import OnDiskFont
from adafruit_fruitjam.peripherals import request_display_config
from adafruit_color_terminal import ColorTerminal

# Routine goto - position output to row, column
def goto(row, column):
    terminal.write(f"\x1B[{int(row)};{int(column)}H")

# Routine cls - clear screen
def cls():
    terminal.write("\x1B[2J")
    goto(1, 1)

def draw_box(width, height, x, y, color_box):
    top_left = '\xDA'
    horizontal = '\xC4'
    top_right = '\xBF'
    vertical = '\xB3'
    bottom_left = '\xC0'
    bottom_right = '\xD9'

    if width < 3 or height < 3:
        return

    # Top line
    out_char(top_left + horizontal*(width - 2) + top_right, x, y, color_box)

    # Middle lines
    for i in range(1, height - 1):
        out_char(vertical + ' '*(width - 2) + vertical, x+i, y, color_box)

    # Bottom line
    out_char(bottom_left + horizontal*(width - 2) + bottom_right, x+height-1,
             y, color_box)

def out_char(value, row, column, color):
    goto(row, column)
    terminal.write(f"\033[3{color}m"+value)

def set_color(palette_index):
    """Set FOREGROUND color only"""
    if not (0 <= palette_index <= 7):  # pylint: disable=superfluous-parens
        raise ValueError("Palette index must be between 0 and 7")
    terminal.write(f"\033[3{palette_index}m")

def set_bgcolor(palette_index):
    """Set BACKGROUND color only"""
    if not (0 <= palette_index <= 7):  # pylint: disable=superfluous-parens
        raise ValueError("Palette index must be between 0 and 7")
    terminal.write(f"\033[4{palette_index}m")

def reset_ansi():
    """Reset to default colors (usually white on black)"""
    terminal.write("\033[0m")

def set_colors(fg_color=None, bg_color=None):
    """Set both foreground and background colors"""
    if fg_color is not None:
        set_color(fg_color)
    if bg_color is not None:
        set_bgcolor(bg_color)

# Use the easy library call to set the resolution
request_display_config(640, 480)

print(f"\nFree before display init: {gc.mem_free()}")

# Initialize display
main_group = displayio.Group()
display = supervisor.runtime.display
display.root_group = main_group

print(f"free: {gc.mem_free()}")

colors = 8

red = 0xff0000
yellow = 0xcccc00
orange = 0xff5500
blue = 0x0000ff
pink = 0xff00ff
purple = 0x5500ff
white = 0xffffff
green = 0x00ff00
aqua = 0x125690
black = 0x000000

terminal_palette = displayio.Palette(colors)
terminal_palette[0] = black
terminal_palette[1] = red
terminal_palette[2] = green
terminal_palette[3] = yellow
terminal_palette[4] = blue
terminal_palette[5] = purple
terminal_palette[6] = aqua
terminal_palette[7] = white

font = OnDiskFont("fonts/cp437_16h.bin")  # LVGL .bin font

char_size = font.get_bounding_box()
print(f"Character size: {char_size}")
print(f"font.bitmap info: {font.bitmap.width}, {font.bitmap.height}")

screen_size = (display.width // char_size[0], display.height // char_size[1])
print(f"Screen size: {screen_size}")
print(f"Screen depth: {display.framebuffer.color_depth} bits")

terminal = ColorTerminal(font, screen_size[0], screen_size[1])
main_group.append(terminal.tilegrid)
print("Created Color Terminal")

# Clear screen and set initial colors properly
cls()

# Test individual colored text - each should stay its own color
out_char("Red (1,1)", 1, 1, 1)         # Red text, then reset
out_char("Green (10,1)", 10, 1, 2)     # Green text, then reset
out_char("Blue (1,30)", 1, 30, 4)      # Blue text, then reset
out_char("Yellow (10,30)", 10, 30, 3)  # Yellow text, then reset
out_char("Magenta (15,1)", 15, 1, 5)   # Magenta text, then reset
out_char("Cyan (15,30)", 15, 30, 6)    # Cyan text, then reset

# Draw box in a specific color (should be yellow)
draw_box(10, 8, 6, 17, 3)

# Write some normal text (should be in default color)
goto(20, 5)
terminal.write("This should be default color")

# Write more colored text using out_char
out_char("Isolated Red", 22, 5, 1)
out_char("Isolated Green", 23, 5, 2)
out_char("Isolated Blue", 24, 5, 4)

# Final text should be in default color
goto(26, 5)
terminal.write("This should also be default color")

print("Done - all colors should be visible simultaneously")
while True:
    pass
