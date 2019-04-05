import time
import board
from adafruit_debouncer import Debouncer
import busio as io
import digitalio
import pulseio
import adafruit_ssd1306

i2c = io.I2C(board.SCL, board.SDA)
reset_pin = digitalio.DigitalInOut(board.D11)
oled = adafruit_ssd1306.SSD1306_I2C(128, 32, i2c, reset=reset_pin)
select = digitalio.DigitalInOut(board.D7)
select.direction = digitalio.Direction.INPUT
select.pull = digitalio.Pull.UP
button_select = Debouncer(select)
play = digitalio.DigitalInOut(board.D9)
play.direction = digitalio.Direction.INPUT
play.pull = digitalio.Pull.UP
button_play = Debouncer(play)

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

# pylint: disable=line-too-long
songbook = {'Twinkle Twinkle': [(C4, 0.5), (C4, 0.5), (G4, 0.5), (G4, 0.5), (A4, 0.5), (A4, 0.5), (G4, 1.0), (0, 0.5),
                                (F4, 0.5), (F4, 0.5), (E4, 0.5), (E4, 0.5), (D4, 0.5), (D4, 0.5), (C4, 0.5), (0, 0.5),
                                (G4, 0.5), (G4, 0.5), (F4, 0.5), (F4, 0.5), (E4, 0.5), (E4, 0.5), (D4, 0.5), (0, 0.5),
                                (G4, 0.5), (G4, 0.5), (F4, 0.5), (F4, 0.5), (E4, 0.5), (E4, 0.5), (D4, 0.5), (0, 0.5),
                                (C4, 0.5), (C4, 0.5), (G4, 0.5), (G4, 0.5), (A4, 0.5), (A4, 0.5), (G4, 1.0), (0, 0.5),
                                (F4, 0.5), (F4, 0.5), (E4, 0.5), (E4, 0.5), (D4, 0.5), (D4, 0.5), (C4, 0.5), (0, 0.5)],

            'ItsyBitsy Spider': [(G4, 0.5), (C4, 0.5), (C4, 0.5), (C4, 0.5), (D4, 0.5), (E4, 0.5), (E4, 0.5), (E4, 0.5), (D4, 0.5), (C4, 0.5), (D4, 0.5), (E4, 0.5), (C4, 0.5), (0, 0.5),
                                 (E4, 0.5), (E4, 0.5), (F4, 0.5), (G4, 0.5), (G4, 0.5), (F4, 0.5), (E4, 0.5), (F4, 0.5), (G4, 0.5), (E4, 0.5), (0, 0.5)],

            'Old MacDonald': [(G4, 0.5), (G4, 0.5), (G4, 0.5), (D4, 0.5), (E4, 0.5), (E4, 0.5), (D4, 0.5), (0, 0.5),
                              (B4, 0.5), (B4, 0.5), (A4, 0.5), (A4, 0.5), (G4, 0.5), (0, 0.5),
                              (D4, 0.5), (G4, 0.5), (G4, 0.5), (G4, 0.5), (D4, 0.5), (E4, 0.5), (E4, 0.5), (D4, 0.5), (0, 0.5),
                              (B4, 0.5), (B4, 0.5), (A4, 0.5), (A4, 0.5), (G4, 0.5), (0, 0.5),
                              (D4, 0.5), (D4, 0.5), (G4, 0.5), (G4, 0.5), (G4, 0.5), (D4, 0.5), (D4, 0.5), (G4, 0.5), (G4, 0.5), (G4, 0.5), (0, 0.5),
                              (G4, 0.5), (G4, 0.5), (G4, 0.5), (G4, 0.5), (G4, 0.5), (G4, 0.5), (0, 0.5),
                              (G4, 0.5), (G4, 0.5), (G4, 0.5), (G4, 0.5), (G4, 0.5), (G4, 0.5), (0, 0.5),
                              (G4, 0.5), (G4, 0.5), (G4, 0.5), (D4, 0.5), (E4, 0.5), (E4, 0.5), (D4, 0.5), (0, 0.5),
                              (B4, 0.5), (B4, 0.5), (A4, 0.5), (A4, 0.5), (G4, 0.5), (0, 0.5)]
           }
# pylint: enable=line-too-long

def play_note(note):
    if note[0] != 0:
        pwm = pulseio.PWMOut(board.D12, duty_cycle = 0, frequency=note[0])
        # Hex 7FFF (binary 0111111111111111) is half of the largest value for a 16-bit int,
        # i.e. 50%
        pwm.duty_cycle = 0x7FFF
    time.sleep(note[1])
    if note[0] != 0:
        pwm.deinit()


def play_song(songname):
    for note in songbook[songname]:
        play_note(note)


def update(songnames, selected):
    oled.fill(0)
    line = 0
    for songname in songnames:
        if line == selected:
            oled.text(">", 0, line * 8)
        oled.text(songname, 10, line * 8)
        line += 1
    oled.show()


selected_song = 0
song_names = sorted(list(songbook.keys()))
while True:
    button_select.update()
    button_play.update()
    update(song_names, selected_song)
    if button_select.fell:
        print("select")
        selected_song = (selected_song + 1) % len(songbook)
    elif button_play.fell:
        print("play")
        play_song(song_names[selected_song])
