# SPDX-FileCopyrightText: 2026 John Park with Claude Opus 5.5 for Adafruit Industries
#
# SPDX-License-Identifier: MIT
"""2D metaballs: shaded blobs that merge, over a glowing field.

Button 1 cycles the hue (double-click it to turn the glow off or on),
button 2 takes a ball away, button 3 adds one.
"""

import gc

import display

# The display first: see voxel_demo.py. The scratch SRAM holds the kernel's
# args and lighting tables (14 KB).
gc.collect()
screen = display.Display(scratch=14336)
screen.text(4, 4, "Metaballs", display.TITLE)
screen.text(250, 4, "reset: menu")
screen.text(4, 224, "B1 hue  B1 twice: glow  B2 fewer  B3 more")

# pylint: disable=wrong-import-position,wrong-import-order
import time

import board
import keypad

import blobs
import metafield

REPORT_SECONDS = 2
DOUBLE_CLICK = 0.35  # seconds: a second press of button 1 within this is a double click

space = metafield.Metaballs(
    display.WIDTH, display.BACK_HEIGHT, "/metaballs.bin", scratch=screen.scratch
)
buttons = keypad.Keys(
    (board.BUTTON1, board.BUTTON2, board.BUTTON3), value_when_pressed=False, pull=True
)
count = blobs.START
gc.collect()
print(
    "metaballs: %d balls (1 to %d), %d hues, free heap %d"
    % (count, blobs.MAX, space.hues, gc.mem_free())
)

start = time.monotonic()
frames = 0
render_ns = 0
report_at = time.monotonic_ns() + REPORT_SECONDS * 1_000_000_000
# a press of button 1 waits here until it can't be the first half of a double click
pending_click = None
while True:
    event = buttons.events.get()
    now = time.monotonic()
    if pending_click is not None and now - pending_click >= DOUBLE_CLICK:
        pending_click = None
        print("hue", space.next_hue())
    if event and event.pressed:
        if event.key_number == 0:
            if pending_click is None:
                pending_click = now
            else:
                pending_click = None
                space.show_glow(not space.glow)
                print("glow", "on" if space.glow else "off")
        elif event.key_number == 1:
            count = max(1, count - 1)
            print("balls", count)
        else:
            count = min(blobs.MAX, count + 1)
            print("balls", count)
    now = time.monotonic() - start
    space.set_balls(blobs.positions(now, display.WIDTH, display.BACK_HEIGHT, count))
    t0 = time.monotonic_ns()
    space.render(screen.back)
    t1 = time.monotonic_ns()
    screen.flip()
    frames += 1
    render_ns += t1 - t0
    if t1 >= report_at:
        print("%.1f fps | render %.1f ms" % (frames / REPORT_SECONDS, render_ns / frames / 1e6))
        frames = render_ns = 0
        report_at += REPORT_SECONDS * 1_000_000_000
