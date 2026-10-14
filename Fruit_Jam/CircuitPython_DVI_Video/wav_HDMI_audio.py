# SPDX-FileCopyrightText: 2026 Anne Barela
#
# SPDX-License-Identifier: MIT
#
# Example: Play a 40kHz wav file over HDMI

import time
import audiocore
import board
import displayio
import picodvi

WAV_FILE = "/piano.wav"  # path to the WAV file on CIRCUITPY

displayio.release_displays()
fb = picodvi.Framebuffer(320, 240, clk_dp=board.CKP, clk_dn=board.CKN,
                         red_dp=board.D0P, red_dn=board.D0N,
                         green_dp=board.D1P, green_dn=board.D1N,
                         blue_dp=board.D2P, blue_dn=board.D2N)
audio = picodvi.AudioOut(fb)  # create soon after the Framebuffer (needs internal RAM)

wave = audiocore.WaveFile(WAV_FILE)  # Open the wav file

if wave.sample_rate != 48000:
    print(f"\n{WAV_FILE} is {wave.sample_rate} Hz; picodvi.AudioOut needs 48000 Hz.")
    print("Resample the file to 48 kHz and try again.\n")
else:
    print(f"\n\nPlaying {WAV_FILE}\n")
    audio.play(wave)
    while audio.playing:
        time.sleep(0.1)  # yield; playback runs in the background
    print("\nPlaying complete\n")

audio.deinit()
wave.deinit()
