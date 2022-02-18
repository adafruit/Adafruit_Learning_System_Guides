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

def play_note(note):
    if note[0] != 0:
        pwm = pwmio.PWMOut(board.D12, duty_cycle = 0, frequency=note[0])
        # Hex 7FFF (binary 0111111111111111) is half of the largest value for a 16-bit int,
        # i.e. 50%
        pwm.duty_cycle = 0x7FFF
    time.sleep(note[1])
    if note[0] != 0:
        pwm.deinit()


a4_quarter = (A4, 0.25)
c4_half = (C4, 0.5)

play_note(a4_quarter)
play_note(c4_half)
