# SPDX-FileCopyrightText: 2026 John Park for Adafruit Industries
#
# SPDX-License-Identifier: GPL-3.0-only
"""v2 spike 1 (docs/PLAN-v2.md): the 2.8" TFT Touch Shield (1947) on the
Metro ESP32-P4. Copy to CIRCUITPY as code.py with adafruit_ili9341,
adafruit_focaltouch and adafruit_display_text in lib/.

Prints the I2C scan (which touch chip), the board.SPI() display setup and
the time of a full-screen refresh, then draws a dot where you touch and
prints each touch.
"""
import time

import board
import displayio
import fourwire
import terminalio
import vectorio
from adafruit_display_text import label

import adafruit_ili9341

displayio.release_displays()
i2c = board.I2C()
while not i2c.try_lock():
    pass
found = i2c.scan()
i2c.unlock()
print("I2C:", [hex(a) for a in found])

spi = board.SPI()
bus = fourwire.FourWire(spi, command=board.D9, chip_select=board.D10, baudrate=40_000_000)
display = adafruit_ili9341.ILI9341(bus, width=320, height=240, auto_refresh=False)

g = displayio.Group()
pal = displayio.Palette(3)
pal[0], pal[1], pal[2] = 0x000000, 0xB061FF, 0xFFFFFF
g.append(vectorio.Rectangle(pixel_shader=pal, width=320, height=240, x=0, y=0, color_index=0))
g.append(label.Label(terminalio.FONT, text="FM-1 v2 spike: touch me", color=0xB061FF, scale=2, x=20, y=20))
dot = vectorio.Circle(pixel_shader=pal, radius=6, x=-20, y=-20, color_index=2)
g.append(dot)
display.root_group = g
t = time.monotonic()
display.refresh()
print("full refresh: %.3f s" % (time.monotonic() - t))

touch = None
if 0x38 in found:
    import adafruit_focaltouch
    touch = adafruit_focaltouch.Adafruit_FocalTouch(i2c)
    print("touch: FocalTouch at 0x38, vendor/chip", hex(touch._read(0xA8, 1)[0]), hex(touch._read(0xA3, 1)[0]))
elif 0x15 in found:
    import adafruit_cst8xx
    touch = adafruit_cst8xx.Adafruit_CST8XX(i2c)
    print("touch: CST8xx at 0x15")
else:
    print("touch: no known chip found")

last = None
while touch:
    pts = touch.touches
    if pts:
        p = pts[0]
        x, y = p["x"], p["y"]
        # The panel reports portrait (240x320); the display is landscape.
        sx, sy = 319 - y, x
        if (x, y) != last:
            print("touch raw", x, y, "screen", sx, sy)
            last = (x, y)
        dot.x, dot.y = sx, sy
        display.refresh()
    time.sleep(0.02)
