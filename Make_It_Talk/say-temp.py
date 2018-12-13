# CircuitPython Speaking Thermometer Example
# Mike Barela

import time
import board
import adafruit_thermistor
import audioio
from digitalio import DigitalInOut, Direction, Pull

D1 = board.BUTTON_A

# Button A setup
button_a = DigitalInOut(D1)
button_a.direction = Direction.INPUT
button_a.pull = Pull.DOWN

# Set up reading the Circuit Playground Express thermistor
thermistor = adafruit_thermistor.Thermistor(
    board.TEMPERATURE, 10000, 10000, 25, 3950)

# Audio playback object and helper to play a full file
aout = audioio.AudioOut(board.A0)

# Play a wave file
def play_file(wavfile):
    wavfile = "/numbers/" + wavfile
    print("Playing", wavfile)
    with open(wavfile, "rb") as f:
        wav = audioio.WaveFile(f)
        aout.play(wav)
        while aout.playing:
            pass

def read_temperature(temp):
    play_file("temperature.wav")
    if temp > 0 and temp < 20:
        filename = str(temp) + ".wav"
        play_file(filename)
    if temp == 20:
        play_file("20.wav")
    if temp > 20 and temp < 30:
        play_file("20.wav")
        filename = str(temp - 20) + ".wav"
        play_file(filename)
    if temp == 30:
        play_file("30.wav")
    if temp > 30 and temp < 40:
        play_file("30.wav")
        filename = str(temp - 30) + ".wav"
        play_file(filename)
    if temp == 40:
        play_file("40.wav")
    if temp > 40 and temp < 50:
        play_file("40.wav")
        filename = str(temp - 40) + ".wav"
        play_file(filename)
    play_file("degrees.wav")
    play_file("celsius.wav")

while True:
    if button_a.value:
        read_temperature(int(thermistor.temperature))
    time.sleep(0.01)
