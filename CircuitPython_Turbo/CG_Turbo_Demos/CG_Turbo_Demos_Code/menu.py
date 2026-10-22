# SPDX-FileCopyrightText: 2026 John Park with Claude Opus 5.5 for Adafruit Industries
#
# SPDX-License-Identifier: MIT
"""The boot menu: the demos, with thumbnails.

Button 3 moves up, button 2 down, button 1 starts the demo. A demo starts as
a fresh run of its own file (supervisor.set_next_code_file and a reload), so
it gets the clean heap its SRAM buffers need; reset comes back here, with
the first demo highlighted.
"""

import board
import displayio
import framebufferio
import keypad
import picodvi
import supervisor
import terminalio
import vectorio
from adafruit_display_text import label

# (name, what it is, file, thumbnail made by tools/make_menu_thumbs.py)
DEMOS = (
    ("VoxelSpace", "terrain fly-over", "/voxel_demo.py", "/menu_voxel.bmp"),
    ("Cornell Box", "progressive path tracer", "/cornell_demo.py", "/menu_cornell.bmp"),
    ("Metaballs", "shaded 2D blobs", "/metaballs_demo.py", "/menu_metaballs.bmp"),
    ("3D Models", "Utah teapot, Stanford bunny", "/meshes_demo.py", "/menu_meshes.bmp"),
)
ROW_TOP = 28
ROW_HEIGHT = 52
NAME = 0xFFFFFF
NAME_SELECTED = 0xFFE040
NOTE = 0x8090A0
HIGHLIGHT = 0x203060

displayio.release_displays()
framebuffer = picodvi.Framebuffer(
    320,
    240,
    clk_dp=board.CKP,
    clk_dn=board.CKN,
    red_dp=board.D0P,
    red_dn=board.D0N,
    green_dp=board.D1P,
    green_dn=board.D1N,
    blue_dp=board.D2P,
    blue_dn=board.D2N,
    color_depth=16,
)
display = framebufferio.FramebufferDisplay(framebuffer, auto_refresh=True)

root = displayio.Group()
highlight_palette = displayio.Palette(1)
highlight_palette[0] = HIGHLIGHT
highlight = vectorio.Rectangle(
    pixel_shader=highlight_palette, width=312, height=ROW_HEIGHT - 2, x=4, y=ROW_TOP - 1
)
root.append(highlight)
root.append(label.Label(terminalio.FONT, text="CG Turbo Demos", color=NAME, scale=2, x=8, y=12))
root.append(label.Label(terminalio.FONT, text="B3 up B2 down B1 go", color=NOTE, x=204, y=13))
names = []
for i, (name, note, _, thumbnail) in enumerate(DEMOS):
    top = ROW_TOP + i * ROW_HEIGHT
    bitmap = displayio.OnDiskBitmap(thumbnail)
    root.append(displayio.TileGrid(bitmap, pixel_shader=bitmap.pixel_shader, x=10, y=top))
    names.append(label.Label(terminalio.FONT, text=name, color=NAME, scale=2, x=102, y=top + 16))
    root.append(names[-1])
    root.append(label.Label(terminalio.FONT, text=note, color=NOTE, x=102, y=top + 36))
display.root_group = root

selected = 0


def show(index):
    highlight.y = ROW_TOP + index * ROW_HEIGHT - 1
    for row, text in enumerate(names):
        text.color = NAME_SELECTED if row == index else NAME


show(selected)
buttons = keypad.Keys(
    (board.BUTTON1, board.BUTTON2, board.BUTTON3), value_when_pressed=False, pull=True
)
while True:
    event = buttons.events.get()
    if not (event and event.pressed):
        continue
    if event.key_number == 2:
        selected = (selected - 1) % len(DEMOS)
        show(selected)
    elif event.key_number == 1:
        selected = (selected + 1) % len(DEMOS)
        show(selected)
    else:
        print("starting", DEMOS[selected][0])
        supervisor.set_next_code_file(DEMOS[selected][2])
        supervisor.reload()
