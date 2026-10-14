# SPDX-FileCopyrightText: 2026 Anne Barela for Adafruit Industries
#
# SPDX-License-Identifier: MIT

# Play a WAV file of any sample rate through DVI/HDMI audio.
# DVI audio in CircuitPython only plays 48 kHz, so non-48 kHz files are
# wrapped in audiospeed.Resampler and played into a 48 kHz mixer.

import time
import audiocore
import audiomixer
import audiospeed
import board
import displayio
import picodvi

WAV_FILE = "/laugh-stereo-11k.wav"  # path to the WAV file on CIRCUITPY
DVI_RATE = 48000                    # the only rate DVI audio accepts
VOLUME = 0.15                       # 0.0 = silent, 1.0 = full, up this if low volumme

displayio.release_displays()
fb = picodvi.Framebuffer(320, 240, clk_dp=board.CKP, clk_dn=board.CKN,
                         red_dp=board.D0P, red_dn=board.D0N,
                         green_dp=board.D1P, green_dn=board.D1N,
                         blue_dp=board.D2P, blue_dn=board.D2N)
audio = picodvi.AudioOut(fb)  # create soon after the Framebuffer (needs internal RAM)

wave = audiocore.WaveFile(WAV_FILE)
print(f"\n{WAV_FILE}: {wave.sample_rate} Hz, {wave.channel_count} channel(s), "
      f"{wave.bits_per_sample}-bit")

if wave.sample_rate == DVI_RATE:
    print("Playing directly\n")
    source = wave
else:
    print(f"Resampling {wave.sample_rate} Hz -> {DVI_RATE} Hz\n")
    source = audiospeed.Resampler(wave)

mixer = audiomixer.Mixer(voice_count=1, buffer_size=2048,
                         sample_rate=DVI_RATE,
                         channel_count=wave.channel_count,
                         bits_per_sample=wave.bits_per_sample,
                         samples_signed=wave.bits_per_sample == 16)
audio.play(mixer)
mixer.voice[0].level = VOLUME
mixer.voice[0].play(source)
while mixer.voice[0].playing:
    time.sleep(0.1)  # yield; playback runs in the background
time.sleep(0.1)      # let the last buffers drain

audio.stop()
mixer.deinit()
if source is not wave:
    source.deinit()

print("Playing complete\n")
audio.deinit()
wave.deinit()
