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

twinkle = [(C4, 0.5), (C4, 0.5), (G4, 0.5), (G4, 0.5), (A4, 0.5), (A4, 0.5), (G4, 0.5), (0, 0.5),
           (F4, 0.5), (F4, 0.5), (E4, 0.5), (E4, 0.5), (D4, 0.5), (D4, 0.5), (C4, 0.5)]

def play_note(note):
    if note[0] != 0:
        pwm = pulseio.PWMOut(board.D12, duty_cycle = 0, frequency=note[0])
        pwm.duty_cycle = 0x7FFF
    time.sleep(note[1])
    if note[0] != 0:
        pwm.deinit()

def play_song(song):
    for note in song:
        play_note(note)

play_song(twinkle)
