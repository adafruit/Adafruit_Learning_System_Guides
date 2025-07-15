# SPDX-FileCopyrightText: 2025 Anne Barela for Adafruit Industries
#
# SPDX-License-Identifier: MIT
#
# Take a BDF or PCF font file and display it on a CircuitPython
# HDMI/DVI display in 320x200 resolution. "." is used for unknown characters

import gc
import displayio
import supervisor
from adafruit_bitmap_font import bitmap_font
from adafruit_display_text import label
from adafruit_fruitjam.peripherals import request_display_config

# Use the easy library call to set the resolution
request_display_config(320, 240)

# Initialize display
display = supervisor.runtime.display
main_group = displayio.Group()
display.root_group = main_group

# Use Labels to display characters that exist in font
font_file = "fonts/cp437-8x12a.pcf"
font = bitmap_font.load_font(font_file)  # Use font = terminalio.FONT for built-in
char_width = 8    # font character width
char_height = 12  # font character height
chars_per_line = 32  # Fixed at 32 characters per line
line_number_width = 35  # Space for line numbers like "000: "

displayed_count = 0
skipped_count = 0

current_x = line_number_width  # Start after line number space
current_y = char_height
current_line_start = 0

# Add first line number
line_label = label.Label(
    font,
    text=f"{current_line_start:03d}: ",
    color=0xFFFFFF,
    x=0,
    y=current_y
)
main_group.append(line_label)

# Try all characters from 0-255 and display ones that exist
for char_code in range(256):
    try:
        # Check if we need to wrap to next line
        if (char_code > 0) and (char_code % chars_per_line == 0):
            current_x = line_number_width  # Reset to after line number
            current_y += char_height + 2  # Add some line spacing
            current_line_start = char_code

            # Stop if we run out of vertical space
            if current_y + char_height > display.height:
                print(f"Display full, stopped at {char_code}")
                break

            # Add line number for this new line
            line_label = label.Label(
                font,
                text=f"{current_line_start:03d}: ",
                color=0xFFFFFF,
                x=0,
                y=current_y
            )
            main_group.append(line_label)

        # Check if glyph exists
        glyph = font.get_glyph(char_code)

        if glyph is None:
            # No glyph available - display a period instead
            display_char = "."
            skipped_count += 1
        else:
            # Glyph exists - display the actual character
            display_char = chr(char_code)

        # Create label for this character (or replacement)
        char_label = label.Label(
            font,
            text=display_char,
            color=0xFFFFFF,
            x=current_x,
            y=current_y
        )

        main_group.append(char_label)
        current_x += char_width
        displayed_count += 1

    except (MemoryError, ValueError) as e:
        print(f"Memory limit reached at char {char_code}")
        break

    # Garbage collection every 16 characters
    if char_code % 16 == 0:
        gc.collect()

print(f"Found {displayed_count - skipped_count} chars with glyphs")
print(f"{skipped_count} missing chars -> periods")
print(f"Free memory: {gc.mem_free()} bytes")

# Keep display active
while True:
    pass
