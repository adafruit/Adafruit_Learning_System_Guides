# SPDX-FileCopyrightText: 2026 Mikey Sklar for Adafruit Industries
#
# SPDX-License-Identifier: MIT

"""4-gray panel info card for the 4.2" 400x300 SSD1683 E-Ink display (#6381, ribbon FPC-190).

Draws a card with the panel's size, chipset, product #, and ribbon label, plus a
4-level gray ramp. displayio + adafruit_ssd1680.
"""

import time

import board
import busio
import displayio
import terminalio
from adafruit_display_text import label
from fourwire import FourWire

import adafruit_ssd1680

displayio.release_displays()

if "EPD_MOSI" in dir(board):  # Feather RP2040 ThinkInk
    spi = busio.SPI(board.EPD_SCK, MOSI=board.EPD_MOSI, MISO=None)
    epd_cs, epd_dc, epd_reset, epd_busy = (
        board.EPD_CS,
        board.EPD_DC,
        board.EPD_RESET,
        board.EPD_BUSY,
    )
else:
    spi = board.SPI()
    epd_cs, epd_dc, epd_reset, epd_busy = board.D9, board.D10, board.D8, board.D7

display_bus = FourWire(
    spi, command=epd_dc, chip_select=epd_cs, reset=epd_reset, baudrate=1000000
)
time.sleep(1)

display = adafruit_ssd1680.SSD1683(
    display_bus,
    width=400,
    height=300,
    busy_pin=epd_busy,
    rotation=0,
    colstart=0,
    vcom=0x30,
    custom_lut=adafruit_ssd1680.SSD1683_GRAY4_LUT,
)

W, H = 400, 300
SIZE, CHIP, PID, RIBBON = '4.2" 400x300', "SSD1683", "#6381", "FPC-190"
FONT_TITLE, FONT_BODY = 3, 4

pal = displayio.Palette(4)
pal[0] = 0xFFFFFF
pal[1] = 0xAAAAAA
pal[2] = 0x555555
pal[3] = 0x000000
WHITE, LIGHT, DARK, BLACK = 0, 1, 2, 3

g = displayio.Group()
bg = displayio.Bitmap(W, H, 4)
bg.fill(WHITE)
g.append(displayio.TileGrid(bg, pixel_shader=pal))

PAD = 6
y = PAD
for text, scale in (
    ("Adafruit ThinkInk", FONT_TITLE),
    (SIZE, FONT_BODY),
    (CHIP + "  " + PID, FONT_BODY),
    (RIBBON, FONT_BODY),
):
    lbl = label.Label(terminalio.FONT, text=text, color=0x000000, scale=scale)
    lbl.anchor_point = (0.0, 0.0)
    lbl.anchored_position = (PAD, y)
    g.append(lbl)
    y += scale * 8 + 6

ramp_top = min(y + 4, H - 16)
ramp_h = H - ramp_top
seg = W // 4
order = (BLACK, DARK, LIGHT, WHITE)
ramp = displayio.Bitmap(W, ramp_h, 4)
for x in range(W):
    col = order[min(x // seg, 3)]
    for ry in range(ramp_h):
        ramp[x, ry] = col
for x in range(W):
    ramp[x, 0] = BLACK
    ramp[x, ramp_h - 1] = BLACK
for ry in range(ramp_h):
    ramp[0, ry] = BLACK
    ramp[W - 1, ry] = BLACK
    for i in range(1, 4):
        ramp[i * seg, ry] = BLACK
g.append(displayio.TileGrid(ramp, pixel_shader=pal, x=0, y=ramp_top))

display.root_group = g
print("refreshing info card...")
display.refresh()
print("done")

time.sleep(display.time_to_refresh + 5)
while True:
    time.sleep(10)
