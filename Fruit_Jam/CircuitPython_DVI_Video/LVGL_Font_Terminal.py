# SPDX-FileCopyrightText: Copyright (c) 2025 Tim C for Adafruit Industries
# SPDX-FileCopyrightText: Copyright (c) 2025 Anne Barela for Adafruit Industries
#
# SPDX-License-Identifier: MIT
#
# Make a simple terminalio.Terminal using an LVGL .bin font
# Shows use of required OnDiskFont function
#
import gc
from terminalio import Terminal
import displayio 
from lvfontio import OnDiskFont
from adafruit_fruitjam.peripherals import request_display_config
import supervisor

# Use the easy library call to set the resolution
request_display_config(640, 480)

print(f"\nfree: {gc.mem_free()}")

# Initialize display

main_group = displayio.Group()
display = supervisor.runtime.display
display.root_group = main_group

print(f"free: {gc.mem_free()}")

font = OnDiskFont("fonts/cp437_16h.bin")  # LVGL .bin font

char_size = font.get_bounding_box()
print(f"Character size: {char_size}")
screen_size = (display.width // char_size[0], display.height // char_size[1])
print(f"Screen size: {screen_size}")

terminal_palette = displayio.Palette(2)
terminal_palette[0] = 0x000000
terminal_palette[1] = 0xFFFFFF

print(f"free: {gc.mem_free()}")
terminal_area = displayio.TileGrid(
    bitmap=font.bitmap,
    width=screen_size[0],
    height=screen_size[1],
    tile_width=char_size[0],
    tile_height=char_size[1],
    pixel_shader=terminal_palette,
)

main_group.append(terminal_area)
terminal = Terminal(terminal_area, font)

message = " Hello World\n This is LVGL text\r\n "
terminal.write(message)

while True:
    pass
