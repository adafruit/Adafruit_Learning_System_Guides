# SPDX-FileCopyrightText: 2025 Melissa LeBlanc-Williams
#
# SPDX-License-Identifier: MIT
import audiocore
import audiobusio
from definitions import PLAY_SOUNDS

class Audio:
    def __init__(self, *, bit_clock, word_select, data):
        self._audio = audiobusio.I2SOut(bit_clock, word_select, data)
        self._wav_files = {}

    def add_sound(self, sound_name, file):
        self._wav_files[sound_name] = file

    def play(self, sound_name, wait=False):
        if not PLAY_SOUNDS:
            return
        if sound_name in self._wav_files:
            with open(self._wav_files[sound_name], "rb") as wave_file:
                wav = audiocore.WaveFile(wave_file)
                self._audio.play(wav)
                if wait:
                    while self._audio.playing:
                        pass
