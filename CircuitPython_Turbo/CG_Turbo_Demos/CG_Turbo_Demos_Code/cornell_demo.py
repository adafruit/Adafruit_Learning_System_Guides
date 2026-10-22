# SPDX-FileCopyrightText: 2026 John Park with Claude Opus 5.5 for Adafruit Industries
#
# SPDX-License-Identifier: MIT
"""Cornell box path tracer: the image refines with every pass.

Button 1 paints the side walls white, or back to red and green. Button 2
starts over from zero samples. Button 3 swaps the two spheres for the
original's two boxes, and back.
"""

import gc

import display

# The display first: see voxel_demo.py. No back buffer: passes draw straight
# to the screen, a row at a time.
gc.collect()
screen = display.Display(scratch=1024, back=False)
T, H = display.TITLE, display.HINT
screen.lines(2, 4, ("Cor-", "nell", "Box"), (T, T, T))
# top to bottom like the Fruit Jam's buttons: B3, B2, B1
screen.lines(2, 70, ("B3", "boxes/", "balls"), (T, H, H))
screen.lines(2, 120, ("B2", "re-", "render"), (T, H, H))
screen.lines(2, 170, ("B1", "color", "off"), (T, H, H))
screen.lines(282, 4, ("reset", "menu"))

# pylint: disable=wrong-import-position,wrong-import-order
import time

import board
import keypad

import cornell
import cornell_scene as scene

box = cornell.Cornell(screen, screen.scratch)
buttons = keypad.Keys(
    (board.BUTTON1, board.BUTTON2, board.BUTTON3), value_when_pressed=False, pull=True
)
gc.collect()
print("Cornell box: %dx%d, free heap %d" % (scene.SIZE, scene.SIZE, gc.mem_free()))

started = time.monotonic()
while True:
    t0 = time.monotonic_ns()
    box.begin_pass()
    restart = None
    for row in range(scene.SIZE):
        box.trace_row(row)
        event = buttons.events.get()
        if event and event.pressed:
            restart = event.key_number
            break
    if restart is not None:
        if restart == 0:
            box.set_white_walls(not box.white_walls)
            print("walls", "white" if box.white_walls else "red and green")
        elif restart == 1:
            box.reset()
            print("restarted")
        else:
            box.set_boxes(not box.boxes)
            print("objects:", "two boxes" if box.boxes else "two spheres")
        started = time.monotonic()
        continue
    box.end_pass()
    print(
        "%d samples | pass %.2f s | %.0f s total"
        % (box.passes, (time.monotonic_ns() - t0) / 1e9, time.monotonic() - started)
    )
