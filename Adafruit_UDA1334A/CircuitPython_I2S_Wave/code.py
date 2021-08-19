import audiocore
import board
import audiobusio

wave_file = open("StreetChicken.wav", "rb")
wave = audiocore.WaveFile(wave_file)

# For Feather M0 Express, ItsyBitsy M0 Express, Metro M0 Express
audio = audiobusio.I2SOut(board.D1, board.D0, board.D9)
# For Feather M4 Express
# audio = audiobusio.I2SOut(board.D1, board.D10, board.D11)
# For Metro M4 Express
# audio = audiobusio.I2SOut(board.D3, board.D9, board.D8)

while True:
    audio.play(wave)
    while audio.playing:
        pass
