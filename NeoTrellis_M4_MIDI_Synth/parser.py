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

# pylint: disable=no-self-use,too-many-return-statements,too-many-branches,inconsistent-return-statements

import header
import events

def log(txt):
    print(txt)
    #pass

class MidiParser(object):

    def __init__(self):
        pass

    def _as_8(self, d):
        return d[0]

    def _as_16(self, d):
        return (d[0] << 8) | d[1]

    def _as_24(self, d):
        return (d[0] << 16) | (d[1] << 8) | d[2]

    def _as_32(self, d):
        return (d[0] << 24) | (d[1] << 16) | (d[2] << 8) | d[3]

    def _as_str(self, d):
        return str(d, encoding='utf8')

    def _read_bytes(self, f, count):
        val = f.read(count)
        return val

    def _read_1_byte(self, f):
        return self._read_bytes(f, 1)

    def _read_2_bytes(self, f):
        return self._read_bytes(f, 2)

    def _read_3_bytes(self, f):
        return self._read_bytes(f, 3)

    def _read_4_bytes(self, f):
        return self._read_bytes(f, 4)

    def _read_8(self, f):
        return self._as_8(self._read_bytes(f, 1))

    def _read_16(self, f):
        return self._as_16(self._read_bytes(f, 2))

    def _read_24(self, f):
        return self._as_24(self._read_bytes(f, 3))

    def _read_32(self, f):
        return self._as_32(self._read_bytes(f, 4))

    def _parse_header(self, f):
        if self._read_4_bytes(f) != b'MThd':
            return None
        if self._read_32(f) != 6:
            return None
        midi_format = self._read_16(f)
        midi_number_of_tracks = self._read_16(f)
        d = self._read_2_bytes(f)
        if d[0] & 0x80:
            ticks_per_frame = d[1]
            negative_SMPTE_format = d[0] & 0x7F
            ticks_per_quarternote = None
        else:
            ticks_per_frame = None
            negative_SMPTE_format = None
            ticks_per_quarternote = (d[0] << 8) | d[1]
        return header.MidiHeader(midi_format,
                                 midi_number_of_tracks,
                                 ticks_per_frame,
                                 negative_SMPTE_format,
                                 ticks_per_quarternote)

    def _parse_variable_length_number(self, f):
        value = self._read_8(f)
        if not value & 0x80:
            return value
        value &= 0x7F
        b = self._read_8(f)
        while b & 0x80:
            value = (value << 7) | (b & 0x7F)
            b = self._read_8(f)
        return (value << 7) | b

    def _parse_F0_sysex_event(self, delta_time, f):
        length = self._parse_variable_length_number(f)
        data = self._read_bytes(f, length)
        return events.F0SysexEvent(delta_time, data)

    def _parse_F7_sysex_event(self, f, delta_time):
        length = self._parse_variable_length_number(f)
        data = self._read_bytes(f, length)
        return events.F7SysexEvent(delta_time, data)

    def _parse_meta_event(self, f, delta_time):
        meta_event_type = self._read_8(f)
        length = self._parse_variable_length_number(f)
        data = self._read_bytes(f, length)
        if meta_event_type == 0x00:
            return events.SequenceNumberMetaEvent(delta_time, self._as_16(data))
        elif meta_event_type == 0x01:
            return events.TextMetaEvent(delta_time, self._as_str(data))
        elif meta_event_type == 0x02:
            return events.CopyrightMetaEvent(delta_time, self._as_str(data))
        elif meta_event_type == 0x03:
            return events.TrackNameMetaEvent(delta_time, self._as_str(data))
        elif meta_event_type == 0x04:
            return events.InstrumentNameMetaEvent(delta_time, self._as_str(data))
        elif meta_event_type == 0x05:
            return events.LyricMetaEvent(delta_time, self._as_str(data))
        elif meta_event_type == 0x06:
            return events.MarkerMetaEvent(delta_time, self._as_str(data))
        elif meta_event_type == 0x07:
            return events.CuePointMetaEvent(delta_time, self._as_str(data))
        elif meta_event_type == 0x20:
            if length != 0x01:
                return None
            track = self._as_8(data)
            if track > 15:
                return None
            return events.ChannelPrefixMetaEvent(delta_time, track)
        elif meta_event_type == 0x2F:
            if length != 0:
                return None
            return events.EndOfTrackMetaEvent(delta_time)
        elif meta_event_type == 0x51:
            if length != 3:
                return None
            return events.SetTempoMetaEvent(delta_time, self._as_24(data))
        elif meta_event_type == 0x54:
            if length != 5:
                return None
            return events.SmpteOffsetMetaEvent(delta_time, data[0], data[1],
                                               data[2], data[3], data[4])
        elif meta_event_type == 0x58:
            if length != 4:
                return None
            return events.TimeSignatureMetaEvent(delta_time, data[0], data[1],
                                                 data[2], data[3])
        elif meta_event_type == 0x59:
            if length != 2:
                return None
            return events.KeySignatureMetaEvent(delta_time, data[0], data[1])
        elif meta_event_type == 0x7F:
            return events.SequencerSpecificMetaEvent(delta_time, data)

    def _parse_midi_event(self, f, delta_time, status):
        if status & 0xF0 != 0xF0:
            command = (status & 0xF0) >> 4
            channel = status & 0x0F
            data_1 = self._read_8(f) & 0x7F
            data_2 = 0
            if command in [8, 9, 10, 11, 14]:
                data_2 = self._read_8(f) & 0x7F
            if command == 8:
                return events.NoteOffEvent(delta_time, channel, data_1, data_2)
            elif command == 9:
                if data_2 == 0:
                    return events.NoteOffEvent(delta_time, channel, data_1, data_2)
                return events.NoteOnEvent(delta_time, channel, data_1, data_2)
            elif command == 10:
                return events.PolyphonicKeyPressureEvent(delta_time, channel, data_1, data_2)
            elif command == 11:
                return events.ControlChangeEvent(delta_time, channel, data_1, data_2)
            elif command == 12:
                return events.ProgramChangeEvent(delta_time, channel, data_1)
            elif command == 13:
                return events.ChannelPressureEvent(delta_time, channel, data_1)
            elif command == 14:
                return events.PitchWheelChangeEvent(delta_time, channel, (data_2 << 7) | data_1)
            return None
        message_id = status & 0x0F
        if message_id == 0:
            manufacturer_id = self._read_8(f)
            data = []
            d = self._read_8(f)
            while d != 0xF7:
                data.append(d)
                d = self._read_8(f)
            return events.SystemExclusiveEvent(delta_time, manufacturer_id, data)
        elif message_id == 2:
            lo7 = self._read_8(f)
            hi7 = self._read_8(f)
            return events.SongPositionPointerEvent(delta_time, (hi7 << 7) | lo7)
        elif message_id == 3:
            return events.SongSelectEvent(delta_time, self._read_8(f))
        elif message_id == 6:
            return events.TuneRequestEvent(delta_time)
        elif message_id == 8:
            return events.TimingClockEvent(delta_time)
        elif message_id == 10:
            return events.StartEvent(delta_time)
        elif message_id == 11:
            return events.ContinueEvent(delta_time)
        elif message_id == 12:
            return events.StopEvent(delta_time)
        elif message_id == 14:
            return events.ActiveSensingEvent(delta_time)
        elif message_id == 15:
            return events.ResetEvent(delta_time)
        return None

    def parse_mtrk_event(self, f):
        delta_time = self._parse_variable_length_number(f)
        event_type = self._read_8(f)
        if event_type == 0xF0:            #sysex event
            event = self._parse_F0_sysex_event(f, delta_time)
        elif event_type == 0xF7:          #sysex event
            event = self._parse_F7_sysex_event(f, delta_time)
        elif event_type == 0xFF:          #meta event
            event = self._parse_meta_event(f, delta_time)
        else:                         #regular midi event
            event = self._parse_midi_event(f, delta_time, event_type)
        log(event)
        return event

    def _parse_track(self, f):
        if self._read_4_bytes(f) != b'MTrk':
            return None
        track_length = self._read_32(f)
        track_data = []
        for _ in range(track_length):
            event = self.parse_mtrk_event(f)
            if event is None:
                log('Error')
            track_data.append(event)
            if isinstance(event, events.EndOfTrackMetaEvent):
                return track_data
        return track_data

    def parse(self, filename):
        with open(filename, 'rb') as f:
            tracks = []
            h = self._parse_header(f)
            for _ in range(h.number_of_tracks):
                tracks.append(self._parse_track(f))
        return (h, tracks)
