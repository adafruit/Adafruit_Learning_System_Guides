import time
import os
import digitalio
import audioio
import board
import adafruit_matrixkeypad

# Membrane 3x4 matrix keypad - https://www.adafruit.com/product/419
cols = [digitalio.DigitalInOut(x) for x in (board.D3, board.D2, board.D1)]
rows = [digitalio.DigitalInOut(x) for x in (board.D7, board.D6, board.D5, board.D4)]

keys = ((1, 2, 3),
        (4, 5, 6),
        (7, 8, 9),
        ('*', 0, '#'))

keypad = adafruit_matrixkeypad.Matrix_Keypad(rows, cols, keys)

wavefiles = [file for file in os.listdir("/sounds/")
             if (file.endswith(".wav") and not file.startswith("._"))]
if len(wavefiles) < 1:
    print("No wav files found in root directory")
else:
    print("Audio files found: ", wavefiles)

# audio output
gc_audio = audioio.AudioOut(board.A0)

def play_file(filename):
    if gc_audio.playing:
        gc_audio.stop()
    f = open(filename, "rb")
    wav = audioio.WaveFile(f)
    gc_audio.play(wav)

while True:
    keys = keypad.pressed_keys
    if keys:
        print("Pressed: ", keys)
        button = keys[0]
        if button > 0 and button < 9:
            soundfile = "/sounds/0"+str(keys[0])+".wav"
            play_file(soundfile)
        if button == 0:
            gc_audio.stop()
    time.sleep(0.1)
