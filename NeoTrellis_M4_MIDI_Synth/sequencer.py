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

import time

class Sequencer(object):

    def __init__(self, synth):
        self._synth = synth
        self.set_tempo(120)
        self._numerator = 4
        self._denominator = 2
        self._clocks_per_metronome_click = 24
        self.set_tempo(500000)
        self.set_time_signature(4, 2, 24)

    def _tick(self):
        time.sleep(self._tick_size)

    def play(self, track):
        for event in track:
            delta_time = 0
            while event.time > delta_time:
                delta_time += 1
                self._tick()
            print('Executing %s' % str(event))
            if event.execute(self):
                return

    def set_tempo(self, tempo):
        print('Setting tempo %d' % tempo)
        self._tempo = tempo
        self._tick_size = tempo / 250000000.0

    def set_time_signature(self, numerator, denominator, clocks_per_metronome_click):
        print('Setting time signature')
        self._numerator = numerator
        self._denominator = denominator
        self._clocks_per_metronome_click = clocks_per_metronome_click

    def note_on(self, key, velocity):
#        print('Note on')
        self._synth.note_on(key, velocity)

    def note_off(self, key, velocity):
#        print('Note off')
        self._synth.note_off(key, velocity)

    def end_track(self):
        pass
#        print('End track')
