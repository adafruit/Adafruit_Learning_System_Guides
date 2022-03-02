# SPDX-FileCopyrightText: 2019 Anne Barela for Adafruit Industries
#
# SPDX-License-Identifier: MIT

# Talking Cane
# for Adafruit Circuit Playground Express with CircuitPython
from adafruit_circuitplayground.express import cpx

# Change this number to adjust touch sensitivity threshold
cpx.adjust_touch_threshold(600)
# Set the tap type: 1=single, 2=double
cpx.detect_taps = 1

# NeoPixel colors used
RED = (90, 0, 0)
BLACK = (0, 0, 0)

cpx.pixels.brightness = 0.1  # set brightness value

# The audio file assigned to the touchpad
audio_file = "imperial_march.wav"

def play_it():
    cpx.pixels.fill(RED)  # Light neopixels
    cpx.play_file(audio_file)  # play audio clip
    print("playing file ", audio_file)
    cpx.pixels.fill(BLACK)  # unlight lights

while True:
    # playback mode. Use the slide switch to change between
    #   trigger via touch or via single tap
    if cpx.switch:
        if cpx.touch_A1:
            play_it()
    else:
        if cpx.tapped:
            play_it()
