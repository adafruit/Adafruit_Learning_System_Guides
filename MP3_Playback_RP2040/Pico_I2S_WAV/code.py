"""
CircuitPython I2S WAV file playback.
Plays a WAV file once.
"""
import audiocore
import board
import audiobusio

audio = audiobusio.I2SOut(board.GP0, board.GP1, board.GP2)

wave_file = open("StreetChicken.wav", "rb")
wav = audiocore.WaveFile(wave_file)

print("Playing wav file!")
audio.play(wav)
while audio.playing:
    pass
print("Done!")
