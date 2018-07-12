import time
import board
import pulseio

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
        pwm = pulseio.PWMOut(board.D12, duty_cycle = 0, frequency=note[0])
        pwm.duty_cycle = 0x7FFF
    time.sleep(note[1])
    if note[0] != 0:
        pwm.deinit()


a4_quarter = (A4, 0.25)
c4_half = (C4, 0.5)

play_note(a4_quarter)
play_note(c4_half)
