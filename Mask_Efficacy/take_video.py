# SPDX-FileCopyrightText: 2020 Carter Nelson for Adafruit Industries
#
# SPDX-License-Identifier: MIT

import time
import math
import os
import RPi.GPIO as GPIO
import simpleaudio as sa
import picamera

camera = picamera.PiCamera()
camera.resolution = (1920, 1080)
VIDEO_LENGTH = 10

BUTTON = 4
GPIO.setmode(GPIO.BCM)
GPIO.setup(BUTTON, GPIO.IN, pull_up_down=GPIO.PUD_UP)

SIN_LENGTH = 500
SIN_AMPLITUDE = 127
SIN_OFFSET = 128
DELTA_PI = 2 * math.pi / SIN_LENGTH
sine_wave = bytes([
     int(SIN_OFFSET + SIN_AMPLITUDE * math.sin(DELTA_PI * i)) for i in range(SIN_LENGTH)
])

def play_tone(length):
    play_back = sa.play_buffer(sine_wave*length, 2, 2, 44100)
    play_back.wait_done()

run_number = int(input("Enter run number:"))

print("Press button when ready.")
while GPIO.input(BUTTON):
    pass

play_tone(100)
camera.start_recording("run_{:03d}.h264".format(run_number))
camera.wait_recording(VIDEO_LENGTH)
camera.stop_recording()
play_tone(100)

err = os.system("MP4Box -add run_{0:03d}.h264 run_{0:03d}.mp4".format(run_number))
