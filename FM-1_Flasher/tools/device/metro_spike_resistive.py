# SPDX-FileCopyrightText: 2026 John Park for Adafruit Industries
#
# SPDX-License-Identifier: GPL-3.0-only
"""Calibrate the resistive 2.8" TFT Touch Shield (1651, TSC2007) on the Metro
ESP32-P4: run from the REPL with the flasher's lib/ on CIRCUITPY, plus
adafruit_ili9341 and adafruit_tsc2007.

    import metro_spike_resistive

Tap each of the four crosses as it appears (a fingernail or stylus is most
accurate). It prints RES_CAL for fm1ui/metro_p4.py, then shows a dot that
follows the touch through fm1ui.metro_p4.Touch with that calibration, so you
can check it reaches the corners. Ctrl-C to stop.
"""
import time

import board
import displayio
import vectorio

from fm1ui import metro_p4 as M

display, _ = M.display_setup()
W, H = M.W, M.H
pal = displayio.Palette(3)
pal[0], pal[1], pal[2] = 0x000000, 0xFFFFFF, 0xFF4040
g = displayio.Group()
g.append(vectorio.Rectangle(pixel_shader=pal, width=W, height=H, x=0, y=0, color_index=0))
cross_h = vectorio.Rectangle(pixel_shader=pal, width=21, height=3, x=-40, y=-40, color_index=1)
cross_v = vectorio.Rectangle(pixel_shader=pal, width=3, height=21, x=-40, y=-40, color_index=1)
dot = vectorio.Circle(pixel_shader=pal, radius=6, x=-20, y=-20, color_index=2)
for s in (cross_h, cross_v, dot):
    g.append(s)
display.root_group = g

i2c = board.I2C()
kind = M.find_touch(i2c)
print("touch chip:", kind)
if kind != "tsc2007":
    raise SystemExit("no TSC2007 at 0x48: is the resistive shield on?")
res = M.Resistive(i2c)

M_ = 30  # the crosses' distance from the edges
TARGETS = ((M_, M_), (W - M_, M_), (M_, H - M_), (W - M_, H - M_))


def show_cross(x, y):
    cross_h.x, cross_h.y = x - 10, y - 1
    cross_v.x, cross_v.y = x - 1, y - 10
    display.refresh()


def press():
    """The average raw (x, y) over a steady press of about 0.4 s."""
    while res.read() is not None:  # wait for the last touch to lift
        time.sleep(0.02)
    pts = []
    while len(pts) < 20:
        p = res.read()
        if p is None:
            pts = []  # start again if the press lifted early
        else:
            pts.append(p)
        time.sleep(0.02)
    return sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts)


raw = []
for tx, ty in TARGETS:
    show_cross(tx, ty)
    print("tap the cross at", tx, ty)
    raw.append(press())
    print("  raw", [int(v) for v in raw[-1]])
show_cross(-40, -40)

(x0, y0), (x1, y1), (x2, y2), (x3, y3) = raw
# Moving right on the screen changes the raw axis that carries screen x.
swap = abs((y1 + y3) - (y0 + y2)) > abs((x1 + x3) - (x0 + x2))
u = [p[1] if swap else p[0] for p in raw]
v = [p[0] if swap else p[1] for p in raw]
u_left, u_right = (u[0] + u[2]) / 2, (u[1] + u[3]) / 2
v_top, v_bottom = (v[0] + v[1]) / 2, (v[2] + v[3]) / 2
ax = (W - 2 * M_) / (u_right - u_left)
ay = (H - 2 * M_) / (v_bottom - v_top)
cal = (swap, round(ax, 4), round(M_ - ax * u_left, 1), round(ay, 4), round(M_ - ay * v_top, 1))
print("RES_CAL =", cal)

res.cal = cal
print("checking: the dot should follow the touch. Ctrl-C to stop.")
while True:
    p = res.sample()
    if p is not None:
        dot.x, dot.y = res.map(*p)
        display.refresh()
    time.sleep(0.01)
