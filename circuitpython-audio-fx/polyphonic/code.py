# SPDX-FileCopyrightText: Copyright 2024 Jeff Epler for Adafruit Industries
# SPDX-License-Identifier: MIT

import os
import collections
import io
import random

import board
import keypad
import audiobusio
import audiomp3
import audiomixer

# Configure the pins to use -- earlier in list = higher priority
pads = [
    board.GP0, board.GP1, board.GP2, board.GP3,
    board.GP4, board.GP5, board.GP6, board.GP7,
    board.GP8, board.GP9, board.GP10, board.GP11,
    board.GP12, board.GP13, board.GP14, board.GP15
]

# Configure max voices to play at once
# (No matter what, at most 4 MP3 decoders)
# If set this number too high, playback will stutter. use lower bit rates or fewer voices
#
# when the number of active samples being played back exceeds the number of voices,
# the top numbered playing sample is stopped. There is no logic to restore a sample that
# got stopped in this way.
#
# (this may not be the same as the old FX board logic)
max_simultaneous_voices = 2
audiodev = audiobusio.I2SOut(
    bit_clock=board.GP16, word_select=board.GP17, data=board.GP18
)

# This is enough to register as an MP3 file with mp3decoder!, allows creating a decoder
# without "opening" a "file"!
EMPTY_MP3_BYTES = b"\xff\xe3"

# THis is actually a valid but very short mp3 file, use it in case the core
# changes and becomes more picky
# EMPTY_MP3_BYTES = b'\xff\xe3\x18\xc4\x00\x00\x00\x03H\x00\x00\x00\x00CIRCUITPYUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUU\xff\xe3\x18\xc4;\x00\x00\x03H\x00\x00\x00\x00UUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUU\xff\xe3\x18\xc4v\x00\x00\x03H\x00\x00\x00\x00UUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUU'


def exists(p):
    try:
        os.stat(p)
        return True
    except OSError:
        return False


def random_choice(seq):
    return seq[random.randrange(len(seq))]


# There's no notification when something finishes playing. So, first loop over
# all triggers; if they're not playing, then calling force_off() doesn't actually
# stop any audio (it's already stopped) but it DOES mark the voice & decoder as
# available. Otherwise, we might needlessly stop some other sample.
def free_stopped_channels():
    for trigger in triggers:
        if trigger._voice and not trigger.playing:
            print("fst")
            trigger.force_off()


# iterating on reversed triggers gives priority to **lower** numbered triggers
def ensure_available_decoder():
    if available_decoders:
        return available_decoders.popleft()

    for trigger in reversed_triggers:
        trigger.force_off()
        if available_decoders:
            break

    return available_decoders.popleft()


def ensure_available_voice():
    if available_voices:
        return available_voices.popleft()

    for trigger in reversed_triggers:
        trigger.force_off()
        if available_voices:
            break

    return available_voices.popleft()


class TriggerBase:
    def __init__(self, prefix):
        self._decoder = None
        self._voice = None
        self._filenames = list(self._gather_filenames(prefix))

    def _gather_filenames(self, prefix):
        for stem in self.stems:
            name_mp3 = f"{prefix}{stem}.mp3"
            if exists(name_mp3):
                yield name_mp3
                continue
            name_wav = f"{prefix}{stem}.wav"
            if exists(name_wav):
                yield name_wav
                continue

    def _get_sample(self, path):
        if path.endswith(".mp3"):
            self._decoder = ensure_available_decoder()
            self._decoder.open(path)
            return self._decoder
        else:
            return audiocore.WaveFile(path)

    def play(self, path, loop=False):
        self.force_off()
        free_stopped_channels()
        sample = self._get_sample(path)
        self._voice = ensure_available_voice()
        self._voice.play(sample, loop=loop)

    def force_off(self):
        print("force off", self)
        voice = self._voice
        if voice is not None:
            print(f"return voice {id(voice)}")
            self._voice = None
            voice.stop()
            available_voices.append(voice)
        decoder = self._decoder
        if decoder is not None:
            print(f"return decoder {id(decoder)}")
            self._decoder = None
            print(list(available_decoders), end=" ")
            available_decoders.append(decoder)
            print("->", list(available_decoders))

    @property
    def playing(self):
        return False if self._voice is None else self._voice.playing

    @classmethod
    def matches(cls, prefix):
        stem = cls.stems[0]
        name_mp3 = f"{prefix}{stem}.mp3"
        name_wav = f"{prefix}{stem}.wav"
        return exists(name_wav) or exists(name_mp3)

    def __repr__(self):
        return f"<{self.__class__.__name__} {self._filenames}{' playing' if self.playing else ''}>"


class NopTrigger(TriggerBase):
    """Does nothing."""

    stems = [""]

    def on_press(self):
        pass

    def on_release(self):
        pass


class BasicTrigger(TriggerBase):
    """Plays a file each time the button is pressed down"""

    stems = [""]

    def on_press(self):
        self.play(self._filenames[0])

    def on_release(self):
        pass


class HoldLoopingTrigger(TriggerBase):
    """Plays a file as long as a button is held down"""

    stems = ["HOLDL"]

    def on_press(self):
        self.play(self._filenames[0], loop=True)

    def on_release(self):
        self.force_off()


class LatchingLoopTrigger(TriggerBase):
    """Toggles playing each time the button is pressed"""

    stems = ["LATCH"]

    def on_press(self):
        if self.playing:
            self.force_off()
        else:
            self.play(self._filenames[0], loop=True)

    def on_release(self):
        pass


class PlayNextTrigger(TriggerBase):
    stems = [f"NEXT{i}" for i in range(10)]

    def __init__(self, prefix):
        super().__init__(prefix)
        self._phase = 0

    def on_press(self):
        self.play(self._filenames[self._phase])
        self._phase = (self._phase + 1) % len(self._filenames)

    def on_release(self):
        pass


class PlayRandomTrigger(TriggerBase):
    stems = [f"RAND{i}" for i in range(10)]

    def __init__(self, prefix):
        super().__init__(prefix)

    def on_press(self):
        self.play(random_choice(self._filenames))

    def on_release(self):
        pass


trigger_classes = [
    BasicTrigger,
    HoldLoopingTrigger,
    LatchingLoopTrigger,
    PlayNextTrigger,
    PlayRandomTrigger,
]


def make_trigger(i):
    prefix = f"T{i:02d}"

    for cls in trigger_classes:
        if not cls.matches(prefix):
            continue
        return cls(prefix)

    return NopTrigger(prefix)


# No matter what, at most 4 MP3 decoders
decoders = [
    audiomp3.MP3Decoder(io.BytesIO(EMPTY_MP3_BYTES))
    for _ in range(min(4, max_simultaneous_voices))
]
print(decoders)
available_decoders = collections.deque(decoders, len(decoders))
print(list(available_decoders))

keys = keypad.Keys(pads, value_when_pressed=False)

triggers = [make_trigger(i) for i in range(len(pads))]


def playback_specs(sample):
    return dict(
        channel_count=sample.channel_count,
        sample_rate=sample.sample_rate,
        bits_per_sample=sample.bits_per_sample,
    )


def check_match_make_mixer(audiodev):
    all_filenames = []
    for trigger in triggers:
        all_filenames.extend(trigger._filenames)

    if not all_filenames:
        raise RuntimeError("*** NO AUDIO FILES FOUND ***")

    if max_simultaneous_voices == 1:
        return [audiodev]

    first_trigger = triggers[0]

    mixer_buffer_size = (1152 * 4) * 4

    specs = None
    for filename in all_filenames:
        sample = first_trigger._get_sample(filename)
        new_specs = playback_specs(sample)
        if specs is None:
            specs = new_specs
        else:
            if specs != new_specs:
                print("*** Audio file specs don't match ***")
                print("{all_filenames[0]}: {specs}")
                print("{filename}: {specs}")
                raise RuntimeError("*** WITH POLYPHONY, ALL MUST MATCH ***")
        first_trigger.force_off()

    print(f"audio specs: {specs}")
    samples_signed = specs["bits_per_sample"] == 16
    mixer = audiomixer.Mixer(
        voice_count=max_simultaneous_voices,
        buffer_size=mixer_buffer_size,
        samples_signed=samples_signed,
        **specs,
    )
    audiodev.play(mixer)

    return list(mixer.voice)


print(triggers)
print(list(available_decoders))

reversed_triggers = list(reversed(triggers))

voices = check_match_make_mixer(audiodev)
print(list(available_decoders))
available_voices = collections.deque(voices, len(voices))

while True:
    if e := keys.events.get():
        print("event", e)
        print("available decoders", *(id(i) for i in available_decoders))
        print("available voices", *(id(i) for i in available_voices))
        trigger = triggers[e.key_number]
        if e.pressed:
            trigger.on_press()
        else:
            trigger.on_release()
        print(triggers)
