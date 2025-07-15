# SPDX-FileCopyrightText: 2025 Anne Barela for Adafruit Industries
#
# SPDX-License-Identifier: MIT
#
# Display an LVGL (.bin) font on a CircuitPython board and
# 640x480 DVI display. Unknown characters will be "."
#
# pylint: disable=broad-except, bare-except

import gc
import displayio
import supervisor
from adafruit_bitmap_font import bitmap_font
from adafruit_display_text import label
from adafruit_fruitjam.peripherals import request_display_config

# Use the easy library call to set the resolution
request_display_config(640, 480)

# Initialize display
display = supervisor.runtime.display
main_group = displayio.Group()
display.root_group = main_group

print(f"Initial memory: {gc.mem_free()}")

# Font loading with error handling and diagnostics
font_file = "fonts/CP437_16h.bin"
try:
    font = bitmap_font.load_font(font_file) # pylint: disable=redefined-outer-name
    print(f"Font loaded: {font_file}")
    print(f"Memory after font load: {gc.mem_free()}")

    # Diagnostic: Check font properties
    try:
        bbox = font.get_bounding_box()
        print(f"Font bounding box: {bbox}")

        # Test a few common characters
        test_chars = [32, 65, 97]  # space, 'A', 'a'
        for char_code in test_chars:
            glyph = font.get_glyph(char_code)
            if glyph:
                print(f"Char {char_code} ('{chr(char_code)}'): OK")
            else:
                print(f"Char {char_code} ('{chr(char_code)}'): Missing")

    except Exception as e:
        print(f"Error checking font properties: {e}")

except Exception as e:
    print(f"Error loading font {font_file}: {e}")
    # Fallback to terminalio font
    import terminalio
    font = terminalio.FONT
    print("Using fallback terminalio.FONT")

# Get actual font dimensions
try:
    font_bbox = font.get_bounding_box()
    char_width = font_bbox[0]
    char_height = font_bbox[1]
    print(f"Actual font size: {char_width}x{char_height}")
except:
    char_width = 9    # fallback
    char_height = 16  # fallback
    print(f"Using fallback font size: {char_width}x{char_height}")

chars_per_line = 32  # Fixed at 32 characters per line
line_number_width = 5 * char_width  # Space for "000: " (5 characters)

displayed_count = 0
skipped_count = 0
current_x = line_number_width  # Start after line number space
current_y = char_height
current_line_start = 0

def create_char_label(font, chr, x, y):
    """Helper function to create character labels with error handling"""
    try:
        return label.Label(font, text=chr, color=0xFFFFFF, x=x, y=y)
    except Exception as e:
        print(f"Error creating label for '{chr}': {e}")
        return None

# Add first line number
text = f"{current_line_start:03d}: "
print(f"Creating line number: '{text}'")

for i, char in enumerate(text):
    char_label = create_char_label(font, char, i * char_width, current_y)
    if char_label:
        main_group.append(char_label)

print(f"Memory after first line number: {gc.mem_free()}")

# Try all characters from 0-255 and display ones that exist
for char_code in range(256):
    try:
        # Check if we need to wrap to next line
        if (char_code > 0) and (char_code % chars_per_line == 0):
            current_x = line_number_width  # Reset to after line number
            current_y += char_height + 4  # Add some line spacing
            current_line_start = char_code

            # Stop if we run out of vertical space
            if current_y + char_height > display.height:
                print(f"Display full, stopped at character {char_code}")
                break

            # Add line number for this new line
            text = f"{current_line_start:03d}: "
            for i, char in enumerate(text):
                char_label = create_char_label(font, char, i * char_width, current_y)
                if char_label:
                    main_group.append(char_label)

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
        char_label = create_char_label(font, display_char, current_x, current_y)
        if char_label:
            main_group.append(char_label)

        current_x += char_width
        displayed_count += 1

    except (MemoryError, ValueError) as e:
        print(f"Memory/Value error at character {char_code}: {e}")
        break
    except Exception as e:
        print(f"Unexpected error at character {char_code}: {e}")
        # Continue with next character
        current_x += char_width
        displayed_count += 1

    # More frequent garbage collection
    if char_code % 8 == 0:
        gc.collect()

    # Progress indicator for debugging
    if char_code % 32 == 0:
        print(f"Processed up to character {char_code}, memory: {gc.mem_free()}")  /
        # pylint: disable=f-string-without-interpolation

print(f"\nCompleted character display:")
print(f"Found {displayed_count - skipped_count} characters with glyphs")
print(f"{skipped_count} missing characters displayed as periods")
print(f"Total labels created: {len(main_group)}")
print(f"Final free memory: {gc.mem_free()} bytes")

# Keep display active
while True:
    pass
