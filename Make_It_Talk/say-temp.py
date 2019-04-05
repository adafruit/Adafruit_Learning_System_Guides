# CircuitPython Speaking Thermometer Example
# Coded for Circuit Playground Express but it may be
# modified for any CircuitPython board with changes to
# button, thermister and audio board definitions.
# Mike Barela for Adafruit Industries, MIT License

import time
import board
import adafruit_thermistor
import audioio
from digitalio import DigitalInOut, Direction, Pull

D1 = board.BUTTON_A
D2 = board.BUTTON_B

# Button A setup (Celsius)
button_a = DigitalInOut(D1)
button_a.direction = Direction.INPUT
button_a.pull = Pull.DOWN
# Button B setup (Fahrenheit)
button_b = DigitalInOut(D2)
button_b.direction = Direction.INPUT
button_b.pull = Pull.DOWN

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

# Function should take an integer -299 to 299 and say it
# Assumes wav files are available for the numbers
def read_temp(temp):
    play_file("temperature.wav")
    if temp < 0:
        play_file("negative.wav")
        temp = - temp
    if temp >= 200:
        play_file("200.wav")
        temp = temp - 200
    elif temp >= 100:
        play_file("100.wav")
        temp = temp - 100
    if (temp >= 0 and temp < 20) or temp % 10 == 0:
        play_file(str(temp) + ".wav")
    else:
        play_file(str(temp // 10) + "0.wav")
        temp = temp - ((temp // 10) * 10 )
        play_file(str(temp) + ".wav")
    play_file("degrees.wav")

while True:
    if button_a.value:
        read_temp(int(thermistor.temperature))
        play_file("celsius.wav")
    if button_b.value:
        read_temp(int(thermistor.temperature * 9 / 5 + 32))
        play_file("fahrenheit.wav")
    time.sleep(0.01)
