# SPDX-FileCopyrightText: Copyright 2024 Jeff Epler for Adafruit Industries
# SPDX-License-Identifier: MIT

# pylint: disable=no-self-use

import os
import io
import random

import board
import digitalio
import keypad
import audiobusio
import audiocore
import audiomp3

# Configure the pins to use -- earlier in list = higher priority
pads = [
    board.GP0, board.GP1, board.GP2, board.GP3,
    board.GP4, board.GP5, board.GP6, board.GP7,
    board.GP8, board.GP9, board.GP10, board.GP11,
    board.GP12, board.GP13, board.GP14, board.GP15
]

# Configure the audio device
audiodev = audiobusio.I2SOut(
    bit_clock=board.GP16, word_select=board.GP17, data=board.GP18
)

led = digitalio.DigitalInOut(board.LED)
led.switch_to_output(False)

# This is enough to register as an MP3 file with mp3decoder!, allows creating a decoder
# without "opening" a "file"!
EMPTY_MP3_BYTES = b"\xff\xe3"

# Create the MP3 decoder object
decoder = audiomp3.MP3Decoder(io.BytesIO(EMPTY_MP3_BYTES))

def exists(p):
    try:
        os.stat(p)
        return True
    except OSError:
        return False


def random_shuffle(seq):
    for i in range(len(seq)):
        j = random.randrange(0, i+1)
        if i != j: # Chance an item remains in same location
            seq[i], seq[j] = seq[j], seq[i]

def random_cycle(seq):
    while True:
        random_shuffle(seq)
        yield from seq

def cycle(seq):
    while True:
        yield from seq

class TriggerBase:
    def __init__(self, prefix):
        self._filenames = list(self._gather_filenames(prefix))
        self._filename_generator = type(self).generate_filenames(self._filenames)
        self.wants_to_play = False

    # Can be cycle or random_cycle
    generate_filenames = cycle

    def on_press(self):
        self.wants_to_play = True

    def on_release(self):
        self.wants_to_play = False

    def on_activate(self):
        self.play_wait()

    def _gather_filenames(self, prefix):
        if self.stems is None:
            return
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
            decoder.open(path)
            return decoder
        else:
            return audiocore.WaveFile(path)

    def play(self, loop=False):
        audiodev.stop()
        path = next(self._filename_generator)
        sample = self._get_sample(path)
        audiodev.play(sample, loop=loop)

    def play_wait(self):
        self.play()
        while audiodev.playing:
            poll_keys()

    def stop(self):
        audiodev.stop()

    @classmethod
    def matches(cls, prefix):
        stem = cls.stems[0]
        name_mp3 = f"{prefix}{stem}.mp3"
        name_wav = f"{prefix}{stem}.wav"
        return exists(name_wav) or exists(name_mp3)

    def __repr__(self):
        return (f"<{self.__class__.__name__} {' '.join(self._filenames)}" +
                f"{' ACTIVE' if self.wants_to_play else ''}>")


class NopTrigger(TriggerBase):
    """Does nothing."""

    stems = None

    def on_activate(self):
        return

class BasicTrigger(TriggerBase):
    """Plays a file each time the button is pressed down"""

    stems = [""]

class HoldLoopingTrigger(TriggerBase):
    """Plays a file as long as a button is held down

    This differs from the basic trigger because the loop stops as soon as the button
    is released """

    stems = ["HOLDL"]

    def on_activate(self):
        self.play(loop=True)
        while audiodev.playing:
            poll_keys()
            for trigger in triggers:
                if trigger is self:
                    break
                if trigger.wants_to_play:
                    self.wants_to_play = False
            if not self.wants_to_play:
                audiodev.stop()

class LatchingLoopTrigger(HoldLoopingTrigger):
    """Plays a file until the button is pressed again

    When the button is pressed again, stops the loop immediately."""

    stems = ["LATCH"]

    def on_press(self):
        if self.wants_to_play or not audiodev.playing:
            self.wants_to_play = not self.wants_to_play

    def on_release(self):
        pass # override default behavior


class PlayNextTrigger(TriggerBase):
    stems = [f"NEXT{i}" for i in range(10)]
    _phase = 0


class PlayRandomTrigger(TriggerBase):
    stems = [f"RAND{i}" for i in range(10)]

    generate_filenames = random_cycle



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


keys = keypad.Keys(pads, value_when_pressed=False)

triggers = [make_trigger(i) for i in range(len(pads))]

def poll_keys():
    while e := keys.events.get():
        trigger = triggers[e.key_number]
        if e.pressed:
            trigger.on_press()
        else:
            trigger.on_release()
        print(e.pressed, trigger)

print(triggers)

reversed_triggers = list(reversed(triggers))

while True:
    poll_keys()
    for t in triggers:
        if t.wants_to_play:
            print(t)
            t.on_activate()
            break
