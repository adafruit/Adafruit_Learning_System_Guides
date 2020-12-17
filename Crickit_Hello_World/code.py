import time
import audioio
import audiocore
import board
import neopixel
from adafruit_crickit import crickit

# Set audio out on speaker
speaker = audioio.AudioOut(board.A0)

# Start playing the file (in the background)
def play_file(wavfile):
    audio_file = open(wavfile, "rb")
    wav = audiocore.WaveFile(audio_file)
    speaker.play(wav)
    while speaker.playing:
        pass

# NeoPixels on the Circuit Playground Express Light Blue
pixels = neopixel.NeoPixel(board.NEOPIXEL, 10, brightness=0.3)
# Fill them with our favorite color "#0099FF light blue" -> 0x0099FF
# (see http://www.color-hex.com/ for more colors and find your fav!)
pixels.fill(0x0099FF)

while True:
    print("Hello world!")
    play_file("hello.wav")       # play Hello World WAV file
    crickit.servo_1.angle = 75   # Set servo angle to 75 degrees
    time.sleep(1.0)              # do nothing for a 1 second
    crickit.servo_1.angle = 135  # Set servo angle to 135 degrees
    time.sleep(1.0)              # do nothing for a 1 second
