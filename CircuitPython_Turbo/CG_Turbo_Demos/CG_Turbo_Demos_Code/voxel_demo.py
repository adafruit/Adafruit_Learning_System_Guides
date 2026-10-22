# SPDX-FileCopyrightText: 2026 John Park with Claude Opus 5.5 for Adafruit Industries
#
# SPDX-License-Identifier: MIT
"""VoxelSpace fly-over.

Button 1 cycles color map, height map, shaded height map. Button 2 cycles the
terrain height: full, 1/2, 1/4, 1/8, flat. Button 3 turns the fog off and on.
"""

import gc

import display

# The display first, before importing anything else: its back buffer needs
# about 136 KB of the internal SRAM, and imported modules take SRAM too.
gc.collect()
screen = display.Display(scratch=8192)
screen.text(4, 4, "VoxelSpace", display.TITLE)
screen.text(250, 4, "reset: menu")
screen.text(4, 224, "B1 color/height/shaded  B2 height  B3 fog")

# pylint: disable=wrong-import-position,wrong-import-order
import time

import board
import keypad

import flight
import voxelspace

SIZE = 512
REPORT_SECONDS = 2
space = voxelspace.VoxelSpace(
    display.WIDTH,
    display.BACK_HEIGHT,
    "/terrain16.bin",
    "/palette.bin",
    SIZE,
    shade_path="/shade.bin",
    scratch=screen.scratch,
)
gc.collect()
print("VoxelSpace: %d distance steps, free heap %d" % (space.rows, gc.mem_free()))

path = flight.Flight(space)
buttons = keypad.Keys(
    (board.BUTTON1, board.BUTTON2, board.BUTTON3), value_when_pressed=False, pull=True
)
frames = 0
render_ns = 0
frame_ns = 0
last = time.monotonic_ns()
report_at = time.monotonic_ns() + REPORT_SECONDS * 1_000_000_000
while True:
    event = buttons.events.get()
    if event and event.pressed:
        if event.key_number == 0:
            space.next_mode()
            print("showing", space.mode)
        elif event.key_number == 1:
            print("terrain height", space.next_height_scale())
        else:
            space.show_fog(not space.fog)
            print("fog", "on" if space.fog else "off")
    path.step()

    t0 = time.monotonic_ns()
    space.render(screen.back)
    t1 = time.monotonic_ns()
    screen.flip()

    now = time.monotonic_ns()
    frames += 1
    render_ns += t1 - t0
    frame_ns += now - last
    last = now
    if now >= report_at:
        print(
            "%.1f fps | render %.1f ms, whole frame %.1f ms"
            % (frames / REPORT_SECONDS, render_ns / frames / 1e6, frame_ns / frames / 1e6)
        )
        frames = render_ns = frame_ns = 0
        report_at += REPORT_SECONDS * 1_000_000_000
