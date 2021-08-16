# Annoy-O-Matic Sound Prank Device
# choose from a variety of sounds and timings to drive your victim bonkers
import time

import board
import pwmio

# pylint: disable=unused-variable,consider-using-enumerate,redefined-outer-name,too-many-locals
piezo = pwmio.PWMOut(board.D0, duty_cycle=0, frequency=440,
                       variable_frequency=True)

# pick the mode here:
#  1 = beep
#  2 = doorbell
#  3 = ringtone
#  4 = crickets
#  5 = teen tone
#  6 = demo mode
annoy_mode = 3

# set general parameters here
interval = 300  # seconds before next annoyance. Default 300 (5 minutes)

# set beep details here
frequency = 5000  # pitch of the beep in Hz.              Default 5000
length = 0.2  # length (duration) of the beep in seconds. Default 0.2
rest = 0.05  # seconds between beep repeats.              Default 0.05

# set beep/cricket details here
repeat = 3  # number of times to repeat the beep/cricket. Default 3

# set ringtone details here
ringtone = 3  # song choices: 1 = Nokia, 2 = iPhone, 3 = Rickroll
ringtone_tempo = 1.6  # suggested Nokia 0.9 , iPhone 1.3 , Rickroll 2.0


def annoy_beep(frequency, length, repeat, rest, interval):
    for _ in range(repeat):
        piezo.frequency = frequency  # 2600 is a nice choice
        piezo.duty_cycle = 65536 // 2  # on 50%
        time.sleep(length)  # sound on
        piezo.duty_cycle = 0  # off
        time.sleep(rest)
    time.sleep(interval)  # wait time until next beep


def annoy_doorbell(interval):
    piezo.frequency = 740
    piezo.duty_cycle = 65536 // 2
    time.sleep(0.85)
    piezo.duty_cycle = 0
    time.sleep(0.05)
    piezo.frequency = 588
    piezo.duty_cycle = 65536 // 2
    time.sleep(1.25)
    piezo.duty_cycle = 0
    time.sleep(interval)


# pylint: disable=too-many-statements
def annoy_ringtone(ringtone, tempo, interval):
    # ringtone 1: Nokia
    # ringtone 2: Apple iPhone
    # ringtone 3: Rick Astley Never Gonna Give You Up

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

    # C4 = 262
    Cs4 = 277
    # Db4 = 277
    D4 = 294
    # Ds4 = 311
    # Eb4 = 311
    E4 = 330
    # F4 = 349
    Fs4 = 370
    # Gb4 = 370
    G4 = 392
    # Gs4 = 415
    # Ab4 = 415
    # A4 = 440
    # As4 = 466
    # Bb4 = 466
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

    if ringtone == 1:
        # Nokia
        nokia_ringtone = [[E6, eighth_note], [D6, eighth_note],
                          [Fs5, quarter_note], [Gs5, quarter_note],
                          [Cs6, eighth_note], [B5, eighth_note],
                          [D5, quarter_note], [E5, quarter_note],
                          [B5, eighth_note], [A5, eighth_note],
                          [Cs5, quarter_note], [E5, quarter_note],
                          [A5, whole_note]]

        for n in range(len(nokia_ringtone)):
            piezo.frequency = (nokia_ringtone[n][0])
            piezo.duty_cycle = 65536 // 2  # on 50%
            time.sleep(nokia_ringtone[n][1])  # note duration
            piezo.duty_cycle = 0  # off
            time.sleep(0.01)

    if ringtone == 2:
        # iPhone Marimba
        iPhone_ringtone = [[B4, eighth_note], [G4, eighth_note],
                           [D5, eighth_note], [G4, eighth_note],
                           [D5, eighth_note], [E5, eighth_note],
                           [D5, eighth_note], [G4, eighth_note],
                           [E5, eighth_note], [D5, eighth_note],
                           [G4, eighth_note], [D5, eighth_note]]

        for n in range(len(iPhone_ringtone)):
            piezo.frequency = (iPhone_ringtone[n][0])
            piezo.duty_cycle = 65536 // 2  # on 50%
            time.sleep(iPhone_ringtone[n][1])  # note duration
            piezo.duty_cycle = 0  # off
            time.sleep(0.01)

    if ringtone == 3:
        # Rickroll
        rick_ringtone = [[A3, sixteenth_note], [B3, sixteenth_note],
                         [D4, sixteenth_note], [B3, sixteenth_note],
                         [Fs4, dotted_eighth_note], [Fs4, sixteenth_note],
                         [Fs4, eighth_note], [E4, eighth_note],
                         [E4, quarter_note],
                         [A3, sixteenth_note], [B3, sixteenth_note],
                         [Cs4, sixteenth_note], [A3, sixteenth_note],
                         [E4, dotted_eighth_note], [E4, sixteenth_note],
                         [E4, eighth_note], [D4, eighth_note],
                         [D4, sixteenth_note], [Cs4, sixteenth_note],
                         [B3, eighth_note]]

        for n in range(len(rick_ringtone)):
            piezo.frequency = (rick_ringtone[n][0])
            piezo.duty_cycle = 65536 // 2  # on 50%
            time.sleep(rick_ringtone[n][1])  # note duration
            piezo.duty_cycle = 0  # off
            time.sleep(0.035)

    time.sleep(interval)


def annoy_crickets(repeat, interval):
    for _ in range(repeat):
        for _ in range(6):
            piezo.frequency = 8000  # 2600 is a nice choice
            piezo.duty_cycle = 65536 // 2  # on 50%
            time.sleep(0.02)  # sound on
            piezo.duty_cycle = 0  # off
            time.sleep(0.05)
        time.sleep(0.2)
    time.sleep(interval)  # wait time until next beep


def annoy_teen_tone(interval):
    piezo.frequency = 17400
    piezo.duty_cycle = 65536 // 2  # on 50%
    time.sleep(10)
    piezo.duty_cycle = 0
    time.sleep(interval)


while True:
    if annoy_mode == 1:
        annoy_beep(frequency, length, repeat, rest, interval)
    elif annoy_mode == 2:
        annoy_doorbell(interval)
    elif annoy_mode == 3:
        annoy_ringtone(ringtone, ringtone_tempo, interval)
    elif annoy_mode == 4:
        annoy_crickets(repeat, interval)
    elif annoy_mode == 5:
        annoy_teen_tone(interval)
    elif annoy_mode == 6:
        annoy_beep(5000, 0.2, 2, 0.05, 3)
        annoy_doorbell(3)
        annoy_ringtone(1, 0.9, 3)
        annoy_ringtone(2, 1.3, 3)
        annoy_ringtone(3, 2.0, 3)
        annoy_crickets(3, 3)
        annoy_teen_tone(6)
