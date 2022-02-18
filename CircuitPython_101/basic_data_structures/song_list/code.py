# SPDX-FileCopyrightText: 2018 Dave Astels for Adafruit Industries
#
# SPDX-License-Identifier: MIT

import time
import board
import pwmio

C4     = 261
C_SH_4 = 277
D4     = 293
D_SH_4 = 311
E4     = 329
F4     = 349
F_SH_4 = 369
G4     = 392
G_SH_4 = 415
A4     = 440
A_SH_4 = 466
B4     = 493

twinkle = [(C4, 0.5), (C4, 0.5), (G4, 0.5), (G4, 0.5), (A4, 0.5), (A4, 0.5), (G4, 0.5), (0, 0.5),
           (F4, 0.5), (F4, 0.5), (E4, 0.5), (E4, 0.5), (D4, 0.5), (D4, 0.5), (C4, 0.5)]

def play_note(note):
    if note[0] != 0:
        pwm = pwmio.PWMOut(board.D12, duty_cycle = 0, frequency=note[0])
        # Hex 7FFF (binary 0111111111111111) is half of the largest value for a 16-bit int,
        # i.e. 50%
        pwm.duty_cycle = 0x7FFF
    time.sleep(note[1])
    if note[0] != 0:
        pwm.deinit()

def play_song(song):
    for note in song:
        play_note(note)

play_song(twinkle)
