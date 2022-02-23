# SPDX-FileCopyrightText: 2018 John Edgar Park for Adafruit Industries
#
# SPDX-License-Identifier: MIT

import board
from adafruit_slideshow import SlideShow, PlayBackDirection
import audioio
import audiocore
import digitalio
import touchio

# Create the slideshow object that plays through once alphabetically.
slideshow = SlideShow(board.DISPLAY)

# Set the touch objects to the first and last teeth
back_pin = board.TOUCH1
forward_pin = board.TOUCH4

# Perform a couple extra steps for the HalloWing M4
try:
    if getattr(board, "CAP_PIN"):
        # Create digitalio objects and pull low for HalloWing M4
        cap_pin = digitalio.DigitalInOut(board.CAP_PIN)
        cap_pin.direction = digitalio.Direction.OUTPUT
        cap_pin.value = False
    if getattr(board, "SPEAKER_ENABLE"):
        # Enable the Speaker
        speaker_enable = digitalio.DigitalInOut(board.SPEAKER_ENABLE)
        speaker_enable.direction = digitalio.Direction.OUTPUT
        speaker_enable.value = True
except AttributeError:
    pass

# Create the touchio objects for HalloWing M0
back_button = touchio.TouchIn(back_pin)
forward_button = touchio.TouchIn(forward_pin)

# Setup the speaker output
a = audioio.AudioOut(board.SPEAKER)

# Helper function that takes in the file name string, splits it at the period, and keeps only the
# beginning of the string. i.e. kitten.bmp becomes kitten.
def basename(file_name):
    return file_name.rsplit('.', 1)[0]


# Helper function to handle wav file playback
def play_file(wav_file_name):
    try:
        data = open(wav_file_name, "rb")
        wav = audiocore.WaveFile(data)
        a.play(wav)
        print("Playing: " + wav_file_name)
        while a.playing:
            pass
        a.stop()
    except OSError:  # Error thrown if it finds a .bmp file with no corresponding .wav file
        # Print the name of the .bmp file with no corresponding .wav file
        print("No corresponding wav file:", slideshow.current_image_name)


# Uses the basename() helper function to strip the .bmp from the file name and add .wav
wav_file = basename(slideshow.current_image_name) + ".wav"
# Uses the play_file() helper function to play the .wav name now saved to wav_file
play_file(wav_file)

while True:
    # Touch the tooth on the right:
    if forward_button.value:
        # Sets the slideshow playback direction to forward
        slideshow.direction = PlayBackDirection.FORWARD
        # Advance the slideshow to the next image
        slideshow.advance()
        # Sets wav_file to the new corresponding .wav file
        wav_file = basename(slideshow.current_image_name) + ".wav"
        # Plays back the new file with the new image
        play_file(wav_file)
    # Touch the tooth on the left:
    if back_button.value:
        # Sets the slideshow playback direction to backward
        slideshow.direction = PlayBackDirection.BACKWARD
        # Advance to the previous image
        slideshow.advance()
        wav_file = basename(slideshow.current_image_name) + ".wav"
        play_file(wav_file)
