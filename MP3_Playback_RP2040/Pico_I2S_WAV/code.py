"""
CircuitPython I2S WAV file playback.
Plays a WAV file for six seconds, pauses
for two seconds, then resumes and plays
the file to the end.
"""
import time
import audiocore
import board
import audiobusio

audio = audiobusio.I2SOut(board.GP0, board.GP1, board.GP2)

wave_file = open("StreetChicken.wav", "rb")
wav = audiocore.WaveFile(wave_file)

print("Playing wav file!")
audio.play(wav)
t = time.monotonic()
while time.monotonic() - t < 6:
    pass

print("Pausing!")
audio.pause()
time.sleep(2)
print("Resuming!")
audio.resume()
while audio.playing:
    pass
print("Done!")
