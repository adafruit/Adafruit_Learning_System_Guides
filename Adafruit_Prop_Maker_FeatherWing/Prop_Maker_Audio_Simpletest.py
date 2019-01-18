"""Simple example to play a wave file"""
# This example only works on Feathers that have analog audio out!
import digitalio
import board
import audioio

WAV_FILE_NAME = "StreetChicken.wav"  # Change to the name of your wav file!

enable = digitalio.DigitalInOut(board.D10)
enable.direction = digitalio.Direction.OUTPUT
enable.value = True

with audioio.AudioOut(board.A0) as audio:  # Speaker connector
    wave_file = open(WAV_FILE_NAME, "rb")
    wave = audioio.WaveFile(wave_file)

    audio.play(wave)
    while audio.playing:
        pass
