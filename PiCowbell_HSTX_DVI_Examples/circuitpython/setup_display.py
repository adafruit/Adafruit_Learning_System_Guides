# SPDX-FileCopyrightText: 2025 Tim Cocks for Adafruit Industries
#
# SPDX-License-Identifier: MIT
import supervisor
import displayio
import picodvi
import framebufferio
import board

def setup_display():
    # Skip if the display is already initialized
    if supervisor.runtime.display is None:
        displayio.release_displays()
        fb = picodvi.Framebuffer(320, 240,
            clk_dp=board.GP14, clk_dn=board.GP15,
            red_dp=board.GP12, red_dn=board.GP13,
            green_dp=board.GP18, green_dn=board.GP19,
            blue_dp=board.GP16, blue_dn=board.GP17,
            color_depth=8)
        display = framebufferio.FramebufferDisplay(fb)

        # set the display onto supervisor.runtime,
        # so it will be available to code.py
        supervisor.runtime.display = display
