import os
import time

import board
import digitalio

from audiomp3 import MP3Decoder

# Updating the display can interfere with MP3 playback if it is not
# done carefully
try:
    board.DISPLAY.auto_refresh = False
except:  # pylint: disable=bare-except
    pass

try:
    from audioio import AudioOut
except ImportError:
    try:
        from audiopwmio import PWMAudioOut as AudioOut
    except ImportError:
        pass  # not always supported by every board!

# The mp3 files on the sd card will be played in alphabetical order
mp3files = sorted(
    "/sd/" + filename
    for filename in os.listdir("/sd")
    if filename.lower().endswith("mp3")
)

voodoo = [1, 2, 3]

# You have to specify some mp3 file when creating the decoder
mp3 = open(mp3files[0], "rb")
decoder = MP3Decoder(mp3)
audio = AudioOut(board.A0, right_channel=board.A1)

speaker_enable = digitalio.DigitalInOut(board.SPEAKER_ENABLE)
speaker_enable.switch_to_output(True)

while True:
    for filename in mp3files:
        print("Playing", filename)

        # Updating the .file property of the existing decoder
        # helps avoid running out of memory (MemoryError exception)
        decoder.file = open(filename, "rb")
        audio.play(decoder)

        # This allows you to do other things while the audio plays!
        while audio.playing:
            time.sleep(1)
