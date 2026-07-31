# SPDX-FileCopyrightText: 2026 Mikey Sklar for Adafruit Industries
#
# SPDX-License-Identifier: MIT

"""Panel info card for Adafruit EPD grayscale displays (CircuitPython adafruit_epd).

Flashes a self-labeling card onto the panel: size/resolution, chipset, Adafruit
product #, and ribbon (FPC) label - handy for telling apart panels that
otherwise look identical on the bench. Card text is monochrome so it works on
every panel; blocks with GRAY_RAMP = True also draw a 4-level gray ramp.

HOW TO USE: uncomment exactly ONE panel block below (its `Panel` import plus the
WIDTH/HEIGHT/ROTATION and SIZE/CHIP/PID/RIBBON/FONT/GRAY_RAMP/VCOM/WIRING
constants) and comment out the block that was active.

Two wiring modes are supported (each block sets WIRING):
  "ZIF"  - a bare panel in the Feather RP2040 ThinkInk 24-pin ZIF (board.EPD_*).
  "WING" - an eInk FeatherWing on a Feather: primary SPI, CS=D9, DC=D10; BUSY is
           not routed on the Wing -> busy_pin=None (timed refresh); RST is on the
           Feather RESET line, so the panel is never deep-slept (power_down is a
           no-op). Run after a power-on/reset.

Other form factors are their own boards - run their dedicated examples instead:
the 2.9" MagTag (#4800, built-in panel, ESP32-S2) and the 2.13" Pi Bonnet
(#4687, Raspberry Pi / Blinka) use different board pins entirely.
"""

# The active panel's class is imported down in the selection block, so this
# import block is intentionally split; noqa silences the import sorter.
import board  # noqa: I001
import busio
import digitalio
import displayio

from adafruit_epd.epd import Adafruit_EPD

# ========================= PANEL SELECTION =========================
# Uncomment ONE block (Panel import + its constants). Comment the others.
# VCOM = None uses the class default (SSD1680=0x1C, SSD1683=0x30); set a value
# to override (the FPC-7519rev.b 2.9" panel wants 0x24).

# ----- 2.66" 296x152 - SSD1680 - #6392 - FPC-A003 - bare ZIF panel -----
from adafruit_epd.ssd1680 import Adafruit_SSD1680_Grayscale4 as Panel

WIDTH, HEIGHT, ROTATION = 152, 296, 3
SIZE, CHIP, PID, RIBBON = '2.66" 296x152', "SSD1680", "#6392", "FPC-A003"
FONT_TITLE, FONT_BODY, GRAY_RAMP, VCOM, WIRING = 2, 2, True, None, "ZIF"

# ----- 2.13" 250x122 - SSD1680(Z) - #4197 / #6383 (bare ZIF) - FPC-7528B -----
# Same panel as the #4195 FeatherWing / #4687 Pi Bonnet (those are FPC-A002 and a
# different form factor). For the #4195 Wing, set WIRING = "WING".
# from adafruit_epd.ssd1680 import Adafruit_SSD1680_Grayscale4 as Panel
# WIDTH, HEIGHT, ROTATION = 122, 250, 3
# SIZE, CHIP, PID, RIBBON = '2.13" 250x122', "SSD1680", "#4197 / #6383", "FPC-7528B"
# FONT_TITLE, FONT_BODY, GRAY_RAMP, VCOM, WIRING = 2, 2, True, None, "ZIF"

# ----- 2.9" 296x128 - SSD1680 - #4777 Wing / #4800 MagTag - FPC-7519rev.b -----
# No bare 2.9" panel exists, so this is the eInk FeatherWing wiring (#4777). On a
# MagTag (#4800) run the dedicated MagTag example instead - different board pins.
# from adafruit_epd.ssd1680 import Adafruit_SSD1680_Grayscale4 as Panel
# WIDTH, HEIGHT, ROTATION = 128, 296, 3
# SIZE, CHIP, PID, RIBBON = '2.9" 296x128', "SSD1680", "#4777 / #4800", "FPC-7519rev.b"
# FONT_TITLE, FONT_BODY, GRAY_RAMP, VCOM, WIRING = 2, 2, True, 0x24, "WING"

# ----- 4.2" 400x300 - SSD1683 - #6381 - FPC-190 (larger fonts) - bare ZIF -----
# from adafruit_epd.ssd1683 import Adafruit_SSD1683_Grayscale4 as Panel
# WIDTH, HEIGHT, ROTATION = 400, 300, 0
# SIZE, CHIP, PID, RIBBON = '4.2" 400x300', "SSD1683", "#6381", "FPC-190"
# FONT_TITLE, FONT_BODY, GRAY_RAMP, VCOM, WIRING = 3, 4, True, None, "ZIF"

# Mono-only panels: import a mono class as Panel and set GRAY_RAMP = False.
# ===================================================================

# A prior displayio script can keep the SPI bus across soft-reloads
# ("EPD_SCK in use"); release it first.
displayio.release_displays()

if WIRING == "WING":
    # eInk FeatherWing on a Feather: RST is on the Feather RESET line, so the
    # panel can't be GPIO-reset to wake from deep sleep -> never deep-sleep it.
    class WingPanel(Panel):
        # override to never deep-sleep a Wing: it has no reset line to wake it
        def power_down(self):
            pass

    Panel = WingPanel

    spi = board.SPI()
    cs = digitalio.DigitalInOut(board.D9)
    dc = digitalio.DigitalInOut(board.D10)
    rst = digitalio.DigitalInOut(board.D11)  # harmless: RST not routed on the Wing
    busy = None  # BUSY not connected on the Wing (timed refresh)
else:  # "ZIF": bare panel in the Feather RP2040 ThinkInk 24-pin connector
    spi = busio.SPI(board.EPD_SCK, board.EPD_MOSI)
    cs = digitalio.DigitalInOut(board.EPD_CS)
    dc = digitalio.DigitalInOut(board.EPD_DC)
    rst = digitalio.DigitalInOut(board.EPD_RESET)
    busy = digitalio.DigitalInOut(board.EPD_BUSY)

_extra = {"vcom": VCOM} if VCOM is not None else {}
display = Panel(
    WIDTH,
    HEIGHT,
    spi,
    cs_pin=cs,
    dc_pin=dc,
    sramcs_pin=None,
    rst_pin=rst,
    busy_pin=busy,
    **_extra,
)
display.rotation = ROTATION  # pylint: disable=attribute-defined-outside-init
W, H = display.width, display.height
print(f"init OK -- {W}x{H}")

# Full white clear pass first to scrub any stale ghosting from a cold panel.
display.fill(Adafruit_EPD.WHITE)
display.display()

# Draw the identity card on a clean background.
display.fill(Adafruit_EPD.WHITE)
PAD = 6
display.text("Adafruit ThinkInk", PAD, PAD, Adafruit_EPD.BLACK, size=FONT_TITLE)
ROW = FONT_BODY * 8 + 4
y = PAD + FONT_TITLE * 8 + 6
display.text(SIZE, PAD, y, Adafruit_EPD.BLACK, size=FONT_BODY)
y += ROW
display.text(CHIP + "  " + PID, PAD, y, Adafruit_EPD.BLACK, size=FONT_BODY)
y += ROW
display.text(RIBBON, PAD, y, Adafruit_EPD.BLACK, size=FONT_BODY)
y += ROW

if GRAY_RAMP:
    # 4-level gray ramp filling the bottom: black | dark | light | white
    ramp_top = min(y + 8, H - 16)
    ramp_h = H - ramp_top
    seg = W // 4
    order = (Adafruit_EPD.BLACK, Adafruit_EPD.DARK, Adafruit_EPD.LIGHT, Adafruit_EPD.WHITE)
    for i, color in enumerate(order):
        x = i * seg
        display.fill_rect(x, ramp_top, seg if i < 3 else W - x, ramp_h, color)
    display.rect(0, ramp_top, W, ramp_h, Adafruit_EPD.BLACK)
    for i in range(1, 4):
        display.vline(i * seg, ramp_top, ramp_h, Adafruit_EPD.BLACK)

print("drawing info card...")
display.display()
print("done")
