# SPDX-FileCopyrightText: 2026 John Park with Claude Opus 5.5 for Adafruit Industries
#
# SPDX-License-Identifier: MIT
"""3D models: the Utah teapot and the Stanford bunny, spinning slowly.

Button 1 switches the model, button 2 the rendering: quad wireframe (the
start), triangle wireframe, Lambert (flat), Phong and Blinn (per-pixel
lighting), and for the teapot texture mapping (Phong lit). Button 3 pauses
and resumes the spin.
"""

import gc

import display

# The display first: see voxel_demo.py. A 240-wide back buffer leaves SRAM
# for the transformed vertices, drawing order and lighting table.
gc.collect()
screen = display.Display(scratch=46080, back_width=240)
screen.text(4, 4, "3D Models", display.TITLE)
screen.text(250, 4, "reset: menu")
screen.text(4, 224, "B1 model  B2 render mode  B3 pause spin")

# pylint: disable=wrong-import-position,wrong-import-order
import time

import board
import keypad

import meshview

SPIN = 0.5  # radians per second
REPORT_SECONDS = 2

viewer = meshview.MeshView(
    ("/teapot.bin", "/bunny.bin"), "/mesh_luts.bin", screen.scratch, ("/teapot_texture.bin", None)
)
buttons = keypad.Keys(
    (board.BUTTON1, board.BUTTON2, board.BUTTON3), value_when_pressed=False, pull=True
)
gc.collect()
print("meshes: free heap %d" % gc.mem_free())
NAMES = ("teapot", "bunny")


def show_shader():
    """The current shader's name in the top border, after the title."""
    screen.fill(70, 4, 160, 12)
    screen.text(70, 4, "shader:")
    screen.text(118, 4, meshview.LABELS[viewer.mode], display.TITLE)


show_shader()

angle = 0.0
spinning = True
last = time.monotonic()
frames = 0
render_ns = 0
report_at = time.monotonic_ns() + REPORT_SECONDS * 1_000_000_000
while True:
    event = buttons.events.get()
    if event and event.pressed:
        if event.key_number == 0:
            viewer.show_model((viewer.model + 1) % len(viewer.models))
            show_shader()  # the bunny has no texture: Phong instead
            print("model", NAMES[viewer.model])
        elif event.key_number == 1:
            viewer.next_mode()
            show_shader()
            print("mode", meshview.MODES[viewer.mode])
        else:
            spinning = not spinning
            print("spin", "on" if spinning else "paused")
    now = time.monotonic()
    if spinning:
        angle += (now - last) * SPIN
    last = now
    viewer.set_rotation(meshview.rotation(angle))
    t0 = time.monotonic_ns()
    viewer.render(screen.back)
    t1 = time.monotonic_ns()
    screen.flip()
    frames += 1
    render_ns += t1 - t0
    if t1 >= report_at:
        print("%.1f fps | render %.1f ms" % (frames / REPORT_SECONDS, render_ns / frames / 1e6))
        frames = render_ns = 0
        report_at += REPORT_SECONDS * 1_000_000_000
