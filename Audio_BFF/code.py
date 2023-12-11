# SPDX-FileCopyrightText: 2023 ladyada for Adafruit Industries
#
# SPDX-License-Identifier: MIT

# Demo audio player that plays random wav files from internal storage or
# SD card. Default pinout matches the Audio BFF for QT Py S2, S3 and RP2040

import os
import random
import audiocore
import board
import audiobusio
import audiomixer
import adafruit_sdcard
import storage
import digitalio

card_cs = digitalio.DigitalInOut(board.A0)
card_cs.direction = digitalio.Direction.INPUT
card_cs.pull = digitalio.Pull.UP
sdcard = None

DATA = board.A1
LRCLK = board.A2
BCLK = board.A3
audio = audiobusio.I2SOut(BCLK, LRCLK, DATA)
mixer = None

button = digitalio.DigitalInOut(board.BUTTON)
button.switch_to_input(pull=digitalio.Pull.UP)

wave_files = []
for filename in sorted(os.listdir("/")):
    filename = filename.lower()
    if filename.endswith(".wav") and not filename.startswith("."):
        wave_files.append(filename)

def open_audio():
    n = random.choice(wave_files)
    print("playing", n)
    f = open(n, "rb")
    w = audiocore.WaveFile(f)
    return f, w

wavefile = 0

while True:
    if not sdcard:
        try:
            sdcard = adafruit_sdcard.SDCard(board.SPI(), card_cs)
            vfs = storage.VfsFat(sdcard)
            storage.mount(vfs, "/sd")
            print("Mounted SD card")
            wave_files = ["/"+file for file in os.listdir('/') if file.endswith('.wav')]
            wave_files += ["/sd/"+file for file in os.listdir('/sd') if file.endswith('.wav')]
            print(wave_files)
        except OSError:
            pass

    if not button.value:
        if mixer and mixer.voice[0].playing:
            print("stopping")
            mixer.voice[0].stop()
            if wavefile:
                wavefile.close()
        else:
            wavefile, wave = open_audio()
            mixer = audiomixer.Mixer(voice_count=1,
                                     sample_rate=wave.sample_rate,
                                     channel_count=wave.channel_count,
                                     bits_per_sample=wave.bits_per_sample,
                                     samples_signed=True)
            mixer.voice[0].level = 0.1
            audio.play(mixer)
            mixer.voice[0].play(wave)

        while not button.value:
            pass
