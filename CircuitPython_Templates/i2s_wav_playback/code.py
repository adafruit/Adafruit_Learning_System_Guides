"""
CircuitPython I2S WAV file playback.
Plays a WAV file once.

Remove this line and all of the following docstring content before submitting to the Learn repo.

Update the three I2S pins to match the wiring chosen for the microcontroller. If you are unsure of
a proper I2S pin combination, run the pin combination script found here:
https://adafru.it/i2s-pin-combo-finder

Update the following pin names to a viable pin combination:
* BIT_CLOCK_PIN
* WORD_SELECT_PIN
* DATA_PIN
"""
import audiocore
import board
import audiobusio

audio = audiobusio.I2SOut(board.BIT_CLOCK_PIN, board.WORD_SELECT_PIN, board.DATA_PIN)

wave_file = open("StreetChicken.wav", "rb")
wav = audiocore.WaveFile(wave_file)

print("Playing wav file!")
audio.play(wav)
while audio.playing:
    pass
print("Done!")
