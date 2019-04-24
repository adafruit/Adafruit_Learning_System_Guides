import time
import board
from digitalio import DigitalInOut, Direction, Pull
import audioio
import neopixel

filename = "electrons.wav"

# The pad our button is connected to:
button = DigitalInOut(board.A4)
button.direction = Direction.INPUT
button.pull = Pull.UP

pixels = neopixel.NeoPixel(board.NEOPIXEL, 10, brightness=1)

# NeoPixel Animation
def simpleCircle(wait):
    PURPLE = (255, 0, 255)
    BLACK = (0, 0, 0)
    CYAN = (0, 255, 255)
    ORANGE = (255, 255, 0)

    for i in range(len(pixels)):
        pixels[i] = PURPLE
        time.sleep(wait)
    for i in range(len(pixels)):
        pixels[i] = CYAN
        time.sleep(wait)
    for i in range(len(pixels)):
        pixels[i] = ORANGE
        time.sleep(wait)
    for i in range(len(pixels)):
        pixels[i] = BLACK
        time.sleep(wait)

# Audio Play File
def play_file(playname):
    print("Playing File " + playname)
    wave_file = open(playname, "rb")
    with audioio.WaveFile(wave_file) as wave:
        with audioio.AudioOut(board.A0) as audio:
            audio.play(wave)
            while audio.playing:
                simpleCircle(.02)
    print("finished")

while True:
    if not button.value:
        play_file(filename)
