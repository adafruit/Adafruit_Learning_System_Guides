import pulseio
import board
import time

piezo = pulseio.PWMOut(board.D0, duty_cycle=0, frequency=440,
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

carmen01 =[[466,  quarter_note],
    [466,  eighth_note],
    [18000, eighth_note],
    [18000, sixteenth_note],
    [494,  eighth_note],
    [18000, sixteenth_note],
    [494,  eighth_note],
    [494,  eighth_note]]

carmen02 =[[415,  quarter_note],
    [415,  eighth_note],
    [18000, eighth_note],
    [18000, sixteenth_note],
    [415,  eighth_note],
    [18000, sixteenth_note],
    [415,  eighth_note],
    [494,  eighth_note]]

carmen03 =[[415,  quarter_note],
    [415,  eighth_note],
    [18000, eighth_note],
    [18000, quarter_note],
    [277,  eighth_note],
    [277,  eighth_note]]

carmen04 =[[466,  eighth_note],
    [466,  sixteenth_note],
    [466,  eighth_note],
    [466,  eighth_note],
    [494,  sixteenth_note],
    [494,  quarter_note],
    [494,  eighth_note],
    [494,  eighth_note]]

carmen05 =[[415,  eighth_note],
    [370,  eighth_note],
    [415,  eighth_note],
    [370,  sixteenth_note],
    [554,  sixteenth_note],
    [554,  sixteenth_note],
    [466,  eighth_note],
    [466,  sixteenth_note],
    [370,  eighth_note],
    [370,  eighth_note]]

carmen06 =[[415,  eighth_note],
    [370,  eighth_note],
    [415,  eighth_note],
    [370,  sixteenth_note],
    [415,  sixteenth_note],
    [415,  sixteenth_note],
    [415,  eighth_note],
    [18000, eighth_note],
    [18000, eighth_note],
    [370,  eighth_note]]

carmen07 =[[415,  eighth_note],
    [370,  eighth_note],
    [415,  eighth_note],
    [370,  sixteenth_note],
    [554,  sixteenth_note],
    [554,  sixteenth_note],
    [466,  eighth_note],
    [466,  sixteenth_note],
    [415,  eighth_note],
    [370,  eighth_note]]

carmen08 =[[370,  eighth_note],
    [18000, eighth_note],
    [370,  eighth_note],
    [370,  eighth_note],
    [415,  eighth_note],
    [18000, eighth_note],
    [415,  eighth_note],
    [18000, eighth_note],
    [165,  eighth_note],
    [165,  eighth_note],
    [165,  eighth_note],
    [165,  sixteenth_note],
    [185,  eighth_note],
    [185,  eighth_note],
    [18000, quarter_note]]

def song_playback(song):
    for n in range(len(song)):
        piezo.frequency = (song[n][0])
        piezo.duty_cycle = 65536//2  # on 50%
        time.sleep(song[n][1])  # note duration
        piezo.duty_cycle = 0  # off
        time.sleep(0.01)

while True:
    song_playback(carmen01)
    song_playback(carmen02)
    song_playback(carmen01)
    song_playback(carmen03)
    song_playback(carmen04)
    song_playback(carmen05)
    song_playback(carmen04)
    song_playback(carmen06)
    song_playback(carmen04)
    song_playback(carmen07)
    song_playback(carmen08)
    song_playback(carmen08)
