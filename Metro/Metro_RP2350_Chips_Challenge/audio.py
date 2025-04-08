# SPDX-FileCopyrightText: 2025 Melissa LeBlanc-Williams
#
# SPDX-License-Identifier: MIT
import audiocore
from definitions import PLAY_SOUNDS

class Audio:
    def __init__(self, audio_bus, sounds):
        self._audio = audio_bus
        self._wav_files = {}
        for sound_name, file in sounds.items():
            self._add_sound(sound_name, file)
        # Play the first sound in the list to initialize the audio system
        self.play(tuple(self._wav_files.keys())[0], wait=True)

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

    def _add_sound(self, sound_name, file):
        self._wav_files[sound_name] = file
