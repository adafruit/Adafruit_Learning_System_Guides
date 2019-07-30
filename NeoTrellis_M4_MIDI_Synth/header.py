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

class MidiHeader(object):

    def __init__(self,
                 midi_format,
                 number_of_tracks,
                 ticks_per_frame,
                 negative_SMPTE_format,
                 ticks_per_quarternote):
        self._format = midi_format
        self._number_of_tracks = number_of_tracks
        self._ticks_per_frame = ticks_per_frame
        self._negative_SMPTE_format = negative_SMPTE_format
        self._ticks_per_quarternote = ticks_per_quarternote

    @property
    def number_of_tracks(self):
        return self._number_of_tracks

    def __str__(self):
        format_string = ('Header - format: {0}, '
                         'track count: {1}, '
                         'ticks per frame: {2}, '
                         'SMPTE: {3}, '
                         'ticks per quarternote: {4}')
        return format_string.format(self._format,
                                    self._number_of_tracks,
                                    self._ticks_per_frame,
                                    self._negative_SMPTE_format,
                                    self._ticks_per_quarternote)
