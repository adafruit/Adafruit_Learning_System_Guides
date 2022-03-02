# SPDX-FileCopyrightText: 2018 John Edgar Park for Adafruit Industries
#
# SPDX-License-Identifier: MIT

"""
Plays the 007 theme song
Gemma M0 with Piezo on D0 and GND
"""

import time

import board
import pwmio

piezo = pwmio.PWMOut(board.D0, duty_cycle=0, frequency=440,
                       variable_frequency=True)

tempo = 2

# tempo is length of whole note in seconds, e.g. 1.5
# set up time signature
whole_note = tempo  # adjust this to change tempo of everything
dotted_whole_note = whole_note * 1.5
# these notes are fractions of the whole note
half_note = whole_note / 2
dotted_half_note = half_note * 1.5
quarter_note = whole_note / 4
dotted_quarter_note = quarter_note * 1.5
eighth_note = whole_note / 8
dotted_eighth_note = eighth_note * 1.5
sixteenth_note = whole_note / 16

# set up note values
A2 = 110
As2 = 117  # 's' stands for sharp: A#2
Bb2 = 117
B2 = 123

C3 = 131
Cs3 = 139
Db3 = 139
D3 = 147
Ds3 = 156
Eb3 = 156
E3 = 165
F3 = 175
Fs3 = 185
Gb3 = 185
G3 = 196
Gs3 = 208
Ab3 = 208
A3 = 220
As3 = 233
Bb3 = 233
B3 = 247

C4 = 262
Cs4 = 277
Db4 = 277
D4 = 294
Ds4 = 311
Eb4 = 311
E4 = 330
F4 = 349
Fs4 = 370
Gb4 = 370
G4 = 392
Gs4 = 415
Ab4 = 415
A4 = 440
As4 = 466
Bb4 = 466
B4 = 494

C5 = 523
Cs5 = 554
Db5 = 554
D5 = 587
Ds5 = 622
Eb5 = 622
E5 = 659
F5 = 698
Fs5 = 740
Gb5 = 740
G5 = 784
Gs5 = 831
Ab5 = 831
A5 = 880
As5 = 932
Bb5 = 932
B5 = 987

# here's another way to express the note pitch, double the previous octave
C6 = C5 * 2
Cs6 = Cs5 * 2
Db6 = Db5 * 2
D6 = D5 * 2
Ds6 = Ds5 * 2
Eb6 = Eb5 * 2
E6 = E5 * 2
F6 = F5 * 2
Fs6 = Fs5 * 2
Gb6 = Gb5 * 2
G6 = G5 * 2
Gs6 = Gs5 * 2
Ab6 = Ab5 * 2
A6 = A5 * 2
As6 = As5 * 2
Bb6 = Bb5 * 2
B6 = B5 * 2

rst = 24000  # rest is just a tone out of normal hearing range

Bond01 = [[B3, half_note],
          [C4, half_note],
          [Cs4, half_note],
          [C4, half_note]]

Bond02 = [[E3, eighth_note],
          [Fs3, sixteenth_note],
          [Fs3, sixteenth_note],
          [Fs3, eighth_note],
          [Fs3, eighth_note],
          [Fs3, eighth_note],
          [E3, eighth_note],
          [E3, eighth_note],
          [E3, eighth_note]]

Bond03 = [[E3, eighth_note],
          [G3, sixteenth_note],
          [G3, sixteenth_note],
          [G3, eighth_note],
          [G3, eighth_note],
          [G3, eighth_note],
          [Fs3, eighth_note],
          [Fs3, eighth_note],
          [Fs3, eighth_note]]

Bond04 = [[E3, eighth_note],
          [G3, sixteenth_note],
          [G3, sixteenth_note],
          [G3, eighth_note],
          [G3, eighth_note],
          [G3, eighth_note],
          [Fs3, eighth_note],
          [Fs3, eighth_note],
          [E3, eighth_note]]

Bond05 = [[Ds4, eighth_note],
          [D4, eighth_note],
          [D4, half_note],
          [B3, eighth_note],
          [A3, eighth_note],
          [B3, whole_note]]

Bond06 = [[E4, eighth_note],
          [G4, quarter_note],
          [Ds5, eighth_note],
          [D5, quarter_note],
          [D5, eighth_note],
          [G4, eighth_note],
          [As4, eighth_note],
          [B4, eighth_note],
          [B4, half_note],
          [B4, quarter_note]]

Bond07 = [[G4, quarter_note],
          [A4, sixteenth_note],
          [G4, sixteenth_note],
          [Fs4, quarter_note],
          [Fs4, eighth_note],
          [B3, eighth_note],
          [E4, eighth_note],
          [Cs4, eighth_note],
          [Cs4, whole_note]]

Bond08 = [[G4, quarter_note],
          [A4, sixteenth_note],
          [G4, sixteenth_note],
          [Fs4, quarter_note],
          [Fs4, eighth_note],
          [B3, eighth_note],
          [Ds4, eighth_note],
          [E4, eighth_note],
          [E4, whole_note]]

Bond09 = [[E4, eighth_note],
          [E4, quarter_note],
          [E4, eighth_note],
          [Fs4, eighth_note],
          [Fs4, sixteenth_note],
          [E4, eighth_note],
          [Fs4, quarter_note]]

Bond10 = [
    [G4, eighth_note],
    [G4, quarter_note],
    [G4, eighth_note],
    [Fs4, eighth_note],
    [Fs4, sixteenth_note],
    [G4, eighth_note],
    [Fs4, quarter_note]]

Bond11 = [[B4, eighth_note],
          [B4, eighth_note],
          [rst, eighth_note],
          [B3, eighth_note],
          [B3, quarter_note],
          [B4, eighth_note],
          [B4, eighth_note],
          [rst, eighth_note],
          [B3, eighth_note],
          [B3, quarter_note],
          [B4, sixteenth_note],
          [B4, eighth_note],
          [B4, sixteenth_note],
          [B4, eighth_note],
          [B4, eighth_note]]

Bond12 = [[E3, eighth_note],
          [G3, quarter_note],
          [Ds4, eighth_note],
          [D4, quarter_note],
          [G3, eighth_note],
          [B3, quarter_note],
          [Fs4, eighth_note],
          [F4, quarter_note],
          [B3, eighth_note],
          [D4, quarter_note],
          [As4, eighth_note],
          [A4, quarter_note],
          [F4, eighth_note],
          [A4, quarter_note],
          [Ds5, eighth_note],
          [D5, quarter_note],
          [rst, eighth_note],
          [rst, quarter_note],
          [Fs4, whole_note]]


def song_playback(song):
    for note in song:
        piezo.frequency = (note[0])
        piezo.duty_cycle = 65536 // 2  # on 50%
        time.sleep(note[1])  # note duration
        piezo.duty_cycle = 0  # off
        time.sleep(0.01)


# this plays the full song roadmap
song_playback(Bond01)
song_playback(Bond01)
song_playback(Bond02)
song_playback(Bond03)
song_playback(Bond02)
song_playback(Bond03)
song_playback(Bond02)
song_playback(Bond04)
song_playback(Bond05)
song_playback(Bond06)
song_playback(Bond07)
song_playback(Bond06)
song_playback(Bond08)
song_playback(Bond09)
song_playback(Bond10)
song_playback(Bond09)
song_playback(Bond10)
song_playback(Bond11)
song_playback(Bond01)
song_playback(Bond01)
song_playback(Bond01)
song_playback(Bond01)
song_playback(Bond05)
song_playback(Bond12)
