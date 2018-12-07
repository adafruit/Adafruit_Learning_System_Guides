"""
NeoTrellis M4 Express MIDI synth

Adafruit invests time and resources providing this open source code.
Please support Adafruit and open source hardware by purchasing
products from Adafruit!

Written by Dave Astels for Adafruit Industries
Copyright (c) 2018 Adafruit Industries
Licensed under the MIT license.

All text above must be included in any redistribution.
"""

# pylint: disable=unused-argument

import time
import board
import audioio

SAMPLE_FOLDER = '/samples/'       # the name of the folder containing the samples
VOICE_COUNT = 8

def capitalize(s):
    if not s:
        return ''
    return s[0].upper() + ''.join([x.lower() for x in s[1:]])


class Synth(object):

    def __init__(self):
        self._voice_name = None
        self._voice_file = None
        self._samples = [None] * 128
        self._channel_count = None
        self._bits_per_sample = None
        self._sample_rate = None
        self._audio = None
        self._mixer = None
        self._currently_playing = [{'key': None, 'voice' : x} for x in range(VOICE_COUNT)]
        self._voices_used = 0

    def _initialize_audio(self):
        if self._audio is None:
            self._audio = audioio.AudioOut(board.A1)
            self._mixer = audioio.Mixer(voice_count=VOICE_COUNT,
                                        sample_rate=16000,
                                        channel_count=1,
                                        bits_per_sample=16,
                                        samples_signed=True)
            self._audio.play(self._mixer)

    def reset(self):
        for i in range(len(self._samples)):
            self._samples[i] = None
        for p in self._currently_playing:
            p['key'] = None

    @property
    def voice(self):
        return self._voice_name

    @voice.setter
    def voice(self, v):
        self._initialize_audio()
        self._voice_name = capitalize(v)
        self._voice_file = '/samples/%s.txt' % v.lower()
        first_note = None
        with open(self._voice_file, "r") as f:
            for line in f:
                cleaned = line.strip()
                if len(cleaned) > 0 and cleaned[0] != '#':
                    key, filename = cleaned.split(',', 1)
                    self._samples[int(key)] = filename.strip()
                    if first_note is None:
                        first_note = filename.strip()
        sound_file = open(SAMPLE_FOLDER+first_note, 'rb')
        wav = audioio.WaveFile(sound_file)
        self._mixer.play(wav, voice=0, loop=False)
        time.sleep(0.5)
        self._mixer.stop_voice(0)

    def _find_usable_voice_for(self, key):
        if self._voices_used == VOICE_COUNT:
            return None
        available = None
        for voice in self._currently_playing:
            if voice['key'] == key:
                return None
            if voice['key'] is None:
                available = voice
        if available is not None:
            self._voices_used += 1
            return available
        return None

    def _find_voice_for(self, key):
        for voice in self._currently_playing:
            if voice['key'] == key:
                return voice
        return None

    def note_on(self, key, velocity):
        fname = self._samples[key]
        if fname is not None:
            f = open(SAMPLE_FOLDER+fname, 'rb')
            wav = audioio.WaveFile(f)
            voice = self._find_usable_voice_for(key)
            if voice is not None:
                voice['key'] = key
                voice['file'] = f
                self._mixer.play(wav, voice=voice['voice'], loop=False)

    def note_off(self, key, velocity):
        if self._voices_used > 0:
            voice = self._find_voice_for(key)
            if voice is not None:
                self._voices_used -= 1
                self._mixer.stop_voice(voice['voice'])
                voice['file'].close()
                voice['file'] = None
                voice['key'] = None
