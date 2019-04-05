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

# Events as defined in http://www.music.mcgill.ca/~ich/classes/mumt306/StandardMIDIfileformat.html
# pylint: disable=unused-argument,no-self-use


class Event(object):

    def __init__(self, delta_time):
        self._delta_time = delta_time

    @property
    def time(self):
        return self._delta_time

    def execute(self, sequencer):
        return False


class F0SysexEvent(Event):
    def __init__(self, delta_time, data):
        Event.__init__(self, delta_time)
        self._data = data


class F7SysexEvent(Event):

    def __init__(self, delta_time, data):
        Event.__init__(self, delta_time)
        self._data = data

class MetaEvent(Event):

    def __init__(self, delta_time):
        Event.__init__(self, delta_time)


class SequenceNumberMetaEvent(MetaEvent):

    def __init__(self, delta_time, sequence_number):
        MetaEvent.__init__(self, delta_time)
        self._sequence_number = sequence_number

    def __str__(self):
        return '%d : Sequence Number : %d' % (self._delta_time, self._sequence_number)


class TextMetaEvent(MetaEvent):
    def __init__(self, delta_time, text):
        MetaEvent.__init__(self, delta_time)
        self._text = text

    def __str__(self):
        return '%d : Text : %s' % (self._delta_time, self._text)


class CopyrightMetaEvent(MetaEvent):

    def __init__(self, delta_time, copyright_notice):
        MetaEvent.__init__(self, delta_time)
        self._copyright_notice = copyright_notice

    def __str__(self):
        return '%d : Copyright : %s' % (self._delta_time, self._copyright_notice)


class TrackNameMetaEvent(MetaEvent):
    def __init__(self, delta_time, track_name):
        MetaEvent.__init__(self, delta_time)
        self._track_name = track_name

    def __str__(self):
        return '%d : Track Name : %s' % (self._delta_time, self._track_name)


class InstrumentNameMetaEvent(MetaEvent):

    def __init__(self, delta_time, instrument_name):
        MetaEvent.__init__(self, delta_time)
        self._instrument_name = instrument_name

    def __str__(self):
        return '%d : Instrument Name : %s' % (self._delta_time, self._instrument_name)


class LyricMetaEvent(MetaEvent):

    def __init__(self, delta_time, lyric):
        MetaEvent.__init__(self, delta_time)
        self._lyric = lyric

    def __str__(self):
        return '%d : Lyric : %s' % (self._delta_time, self._lyric)


class MarkerMetaEvent(MetaEvent):

    def __init__(self, delta_time, marker):
        MetaEvent.__init__(self, delta_time)
        self._marker = marker

    def __str__(self):
        return '%d : Marker : %s' % (self._delta_time, self._marker)


class CuePointMetaEvent(MetaEvent):

    def __init__(self, delta_time, cue):
        MetaEvent.__init__(self, delta_time)
        self._cue = cue

    def __str__(self):
        return '%d : Cue : %s' % (self._delta_time, self._cue)


class ChannelPrefixMetaEvent(MetaEvent):

    def __init__(self, delta_time, channel):
        MetaEvent.__init__(self, delta_time)
        self._channel = channel

    def __str__(self):
        return '%d: Channel Prefix : %d' % (self._delta_time, self._channel)


class EndOfTrackMetaEvent(MetaEvent):

    def __init__(self, delta_time):
        MetaEvent.__init__(self, delta_time)

    def __str__(self):
        return '%d: End Of Track' % (self._delta_time)

    def execute(self, sequencer):
        sequencer.end_track()
        return True


class SetTempoMetaEvent(MetaEvent):

    def __init__(self, delta_time, tempo):
        MetaEvent.__init__(self, delta_time)
        self._tempo = tempo

    def __str__(self):
        return '%d: Set Tempo : %d' % (self._delta_time, self._tempo)

    def execute(self, sequencer):
        sequencer.set_tempo(self._tempo)
        return False


class SmpteOffsetMetaEvent(MetaEvent):

    def __init__(self, delta_time, hour, minute, second, fr, rr):
        MetaEvent.__init__(self, delta_time)
        self._hour = hour
        self._minute = minute
        self._second = second
        self._fr = fr
        self._rr = rr

    def __str__(self):
        return '%d : SMPTE Offset : %02d:%02d:%02d %d %d' % (self._delta_time,
                                                             self._hour,
                                                             self._minute,
                                                             self._second,
                                                             self._fr,
                                                             self._rr)


class TimeSignatureMetaEvent(MetaEvent):

    def __init__(self, delta_time, nn, dd, cc, bb):
        MetaEvent.__init__(self, delta_time)
        self._numerator = nn
        self._denominator = dd
        self._cc = cc
        self._bb = bb

    def __str__(self):
        return '%d : Time Signature : %d %d %d %d' % (self._delta_time,
                                                      self._numerator,
                                                      self._denominator,
                                                      self._cc,
                                                      self._bb)

    def execute(self, sequencer):
        sequencer.set_time_signature(self._numerator, self._denominator, self._cc)
        return False


class KeySignatureMetaEvent(MetaEvent):

    def __init__(self, delta_time, sf, mi):
        MetaEvent.__init__(self, delta_time)
        self._sf = sf
        self._mi = mi

    def __str__(self):
        return '%d : Key Signature : %d %d' % (self._delta_time, self._sf, self._mi)


class SequencerSpecificMetaEvent(MetaEvent):

    def __init__(self, delta_time, data):
        MetaEvent.__init__(self, delta_time)
        self._data = data


class MidiEvent(Event):

    def __init__(self, delta_time, channel):
        Event.__init__(self, delta_time)
        self._channel = channel


class NoteOffEvent(MidiEvent):

    def __init__(self, delta_time, channel, key, velocity):
        MidiEvent.__init__(self, delta_time, channel)
        self._key = key
        self._velocity = velocity

    def __str__(self):
        return '%d : Note Off : key %d, velocity %d' % (self._delta_time,
                                                        self._key,
                                                        self._velocity)

    def execute(self, sequencer):
        sequencer.note_off(self._key, self._velocity)
        return False


class NoteOnEvent(MidiEvent):

    def __init__(self, delta_time, channel, key, velocity):
        MidiEvent.__init__(self, delta_time, channel)
        self._key = key
        self._velocity = velocity

    def __str__(self):
        return '%d : Note On : key %d, velocity %d' % (self._delta_time,
                                                       self._key,
                                                       self._velocity)

    def execute(self, sequencer):
        sequencer.note_on(self._key, self._velocity)
        return False


class PolyphonicKeyPressureEvent(MidiEvent):

    def __init__(self, delta_time, channel, key, pressure):
        MidiEvent.__init__(self, delta_time, channel)
        self._key = key
        self._pressure = pressure

    def __str__(self):
        return '%d : Poly Key Pressure : key %d, velocity %d' % (self._delta_time,
                                                                 self._key,
                                                                 self._pressure)


class ControlChangeEvent(MidiEvent):

    def __init__(self, delta_time, channel, controller, value):
        MidiEvent.__init__(self, delta_time, channel)
        self._controller = controller
        self._value = value

    def __str__(self):
        return '%d : Control Change : controller %d, value %d' % (self._delta_time,
                                                                  self._controller,
                                                                  self._value)



class ProgramChangeEvent(MidiEvent):

    def __init__(self, delta_time, channel, program_number):
        MidiEvent.__init__(self, delta_time, channel)
        self._program_number = program_number

    def __str__(self):
        return '%d : Program Change : program %d' % (self._delta_time,
                                                     self._program_number)

class ChannelPressureEvent(MidiEvent):

    def __init__(self, delta_time, channel, pressure):
        MidiEvent.__init__(self, delta_time, channel)
        self._pressure = pressure

    def __str__(self):
        return '%d : Channel Pressure : %d' % (self._delta_time, self._channel)

class PitchWheelChangeEvent(MidiEvent):

    def __init__(self, delta_time, channel, value):
        MidiEvent.__init__(self, delta_time, channel)
        self._value = value

    def __str__(self):
        return '%d : Pitch Wheel Change : %d' % (self._delta_time, self._value)


class SystemExclusiveEvent(MidiEvent):

    def __init__(self, delta_time, channel, data):
        MidiEvent.__init__(self, delta_time, channel)
        self._data = data


class SongPositionPointerEvent(MidiEvent):

    def __init__(self, delta_time, beats):
        MidiEvent.__init__(self, delta_time, None)
        self._beats = beats

    def __str__(self):
        return '%d: SongPositionPointerEvent(beats %d)' % (self._delta_time,
                                                           self._beats)


class SongSelectEvent(MidiEvent):

    def __init__(self, delta_time, song):
        MidiEvent.__init__(self, delta_time, None)
        self._song = song

    def __str__(self):
        return '%d: SongSelectEvent(song %d)' % (self._delta_time,
                                                 self._song)


class TuneRequestEvent(MidiEvent):

    def __init__(self, delta_time):
        MidiEvent.__init__(self, delta_time, None)

    def __str__(self):
        return '%d : Tune Request' % (self._delta_time)


class TimingClockEvent(MidiEvent):

    def __init__(self, delta_time):
        MidiEvent.__init__(self, delta_time, None)

    def __str__(self):
        return '%d : Timing Clock' % (self._delta_time)


class StartEvent(MidiEvent):

    def __init__(self, delta_time):
        MidiEvent.__init__(self, delta_time, None)

    def __str__(self):
        return '%d : Start' % (self._delta_time)


class ContinueEvent(MidiEvent):

    def __init__(self, delta_time):
        MidiEvent.__init__(self, delta_time, None)

    def __str__(self):
        return '%d : Continue' % (self._delta_time)


class StopEvent(MidiEvent):

    def __init__(self, delta_time):
        MidiEvent.__init__(self, delta_time, None)

    def __str__(self):
        return '%d : Stop' % (self._delta_time)


class ActiveSensingEvent(MidiEvent):

    def __init__(self, delta_time):
        MidiEvent.__init__(self, delta_time, None)

    def __str__(self):
        return '%d : Active Sensing' % (self._delta_time)


class ResetEvent(MidiEvent):

    def __init__(self, delta_time):
        MidiEvent.__init__(self, delta_time, None)

    def __str__(self):
        return '%d : Reset' % (self._delta_time)
