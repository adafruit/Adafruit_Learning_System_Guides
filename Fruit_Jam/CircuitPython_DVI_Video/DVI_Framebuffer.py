# SPDX-FileCopyrightText: 2025 Anne Barela for Adafruit Industries
#
# SPDX-License-Identifier: MIT
#
# Set up a DVI display using Framebufferio and displayio
# Text and drawing is all done vis displayio
#
import sys
import microcontroller
import board
import displayio
import terminalio
import framebufferio
import picodvi
from adafruit_display_text import label

# Initialize displayio
displayio.release_displays()
try:
    fb = picodvi.Framebuffer(640, 480, clk_dp=board.CKP, clk_dn=board.CKN,
                             red_dp=board.D0P, red_dn=board.D0N,
                             green_dp=board.D1P, green_dn=board.D1N,
                             blue_dp=board.D2P, blue_dn=board.D2N,
                             color_depth=4)
except ValueError as e:
    print("Framebuffer error: ", e)
    # Per picodvi/Framebuffer_RP2350.c only 320x240 at 8 & 16 bits work
    # Show error
    sys.exit(e)

display = framebufferio.FramebufferDisplay(fb)
display_group = displayio.Group()

display.root_group = display_group

# Create labels
# pylint: disable=line-too-long
text = "         1         2         3         4         5         6         7         8         9         0         1         2"
text_area = label.Label(terminalio.FONT, text=text, color=0xFFFFFF)
text_area.x = 0
text_area.y = 5
display_group.append(text_area)
# pylint: disable=line-too-long
text = "123456789012345678901234567890123456789012345678901234567890123456789012345678901234567890123456789012345678901234567890"
text_area = label.Label(terminalio.FONT, text=text, color=0xFFFFFF)
text_area.x = 0
text_area.y = 15
display_group.append(text_area)
text = f"Microcontroller speed: {microcontroller.cpu.frequency}"
text_area = label.Label(terminalio.FONT, text=text, color=0xFFFFFF)
text_area.x = 5
text_area.y = 40
display_group.append(text_area)

while True:
    pass
