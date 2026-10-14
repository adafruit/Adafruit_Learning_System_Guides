# SPDX-FileCopyrightText: 2026 Anne Barela for Adafruit Industries
#
# SPDX-License-Identifier: MIT

import array
import math
import time
import audiocore
import board
import displayio
import picodvi

displayio.release_displays()  # Ensure previous video framebuffers are gone

fb = picodvi.Framebuffer(320, 240, clk_dp=board.CKP, clk_dn=board.CKN,
                         red_dp=board.D0P, red_dn=board.D0N,
                         green_dp=board.D1P, green_dn=board.D1N,
                         blue_dp=board.D2P, blue_dn=board.D2N)

# Make the HDMI audio object (do this directly after creating the framebuffer for memory management)
audio = picodvi.AudioOut(fb)

# Make a 1,000 Hz sine wave
sine = array.array("h", [int(1000 * math.sin(math.pi * 2 * i / 48)) for i in range(48)])
# Make an audio sample
tone = audiocore.RawSample(sine, sample_rate=48000)

print("\n\nPlaying started\n")

audio.play(tone, loop=True)

start = time.monotonic()
while time.monotonic() - start < 5:  # Play the tone for 5 seconds
    time.sleep(0.1)                  # yield; the tone keeps looping in the background
audio.stop()

print("\nPlaying complete\n")
