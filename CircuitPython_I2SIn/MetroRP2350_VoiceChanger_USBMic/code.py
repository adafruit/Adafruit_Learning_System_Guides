# SPDX-FileCopyrightText: 2026 Tim Cocks for Adafruit Industries
#
# SPDX-License-Identifier: MIT
"""USB Voice changing microphone. Gets audio from I2S mic, applies
filters and effects, then passes the modified audio out via USB to
the host computer.

Must enable usb_microphone in boot.py.


Wiring:
  bclk          -> board.D5
  word select   -> board.D6
  data          -> board.D9

"""
import audiodelays
import board
import audioi2sin
import usb_audio
import audiofreeverb
import audiofilters

usb_mic = usb_audio.usb_microphone

with audioi2sin.I2SIn(
    board.D5, board.D6, board.D9, sample_rate=16000, bit_depth=16
) as i2s_mic:

    pitch_shift = audiodelays.PitchShift(
        semitones=5.0,
        mix=0.5,
        window=2048,
        overlap=256,
        buffer_size=1024,
        channel_count=1,
        sample_rate=16000,
    )
    pitch_shift.play(i2s_mic)

    reverb = audiofreeverb.Freeverb(
        roomsize=0.35,
        damp=0.25,
        buffer_size=1024,
        channel_count=1,
        sample_rate=16000,
        mix=0.45,
    )
    reverb.play(pitch_shift)

    # amp used for pre_gain only to boost volume
    amp = audiofilters.Distortion(
        pre_gain=23.6,
        drive=0.00,
        mode=audiofilters.DistortionMode.LOFI,
        soft_clip=True,
        mix=1.0,
        buffer_size=1024,
        sample_rate=16000,
        bits_per_sample=16,
        samples_signed=True,
        channel_count=1,
    )
    amp.play(reverb)
    usb_mic.play(amp)

    try:
        while True:
            pass
    except KeyboardInterrupt:
        pass
