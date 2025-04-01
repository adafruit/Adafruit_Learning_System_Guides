# SPDX-FileCopyrightText: 2025 Melissa LeBlanc-Williams
#
# SPDX-License-Identifier: MIT

import time
import board
import picodvi
import framebufferio
import displayio
from game import Game
from definitions import SECOND_LENGTH, TICKS_PER_SECOND

# Disable auto-reload to prevent the game from restarting
# TODO: Enable after testing
#import supervisor
#supervisor.runtime.autoreload = False

# Change this to use a different data file
DATA_FILE = "CHIPS.DAT"

displayio.release_displays()

audio_settings = {
    'bit_clock': board.D9,
    'word_select': board.D10,
    'data': board.D11
}

fb = picodvi.Framebuffer(320, 240, clk_dp=board.CKP, clk_dn=board.CKN,
                                   red_dp=board.D0P, red_dn=board.D0N,
                                   green_dp=board.D1P, green_dn=board.D1N,
                                   blue_dp=board.D2P, blue_dn=board.D2N,
                                   color_depth=8)
display = framebufferio.FramebufferDisplay(fb)

game = Game(display, DATA_FILE, **audio_settings)
tick_length = SECOND_LENGTH / 1000 / TICKS_PER_SECOND
while True:
    start = time.monotonic()
    game.tick()
    while time.monotonic() - start < tick_length:
        pass
