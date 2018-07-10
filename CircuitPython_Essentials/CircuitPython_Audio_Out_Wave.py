import time
import audioio
import board
import digitalio

button = digitalio.DigitalInOut(board.A1)
button.direction = digitalio.Direction.INPUT
button.pull = digitalio.Pull.UP

wave_file = open("StreetChicken.wav", "rb")
wave = audioio.WaveFile(wave_file)
audio = audioio.AudioOut(board.A0)

while True:
    audio.play(wave)
    t = time.monotonic()
    while time.monotonic() - t < 6:
        pass
    audio.pause()
    print("Waiting for button press to continue!")
    while button.value:
        pass
    audio.resume()
    while audio.playing:
        pass
    print("Done!")
