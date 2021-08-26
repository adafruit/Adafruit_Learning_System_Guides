"""
CircuitPython multiple MP3 playback example.
Plays two MP3 files consecutively, once time each.

Remove this line and all of the following docstring content before submitting to the Learn repo.

INCLUDE THE MP3 FILES IN THIS DIRECTORY IN A DIRECTORY WITH THE RESULTING CODE.PY FILE.

Choose the setup section appropriate for the board into which this template code is going. The
default is for SAMD51 boards.

If the setup is commented out, uncomment it. Regardless, ALWAYS delete the comment above the chosen
setup is commented out, uncomment it. Regardless, ALWAYS delete the comment above the chosen
imports/setup and all other setup options so that the example includes ONLY the appropriate list
of imports and the hardware setup. For example, a generic SAMD51 example should be:

    import board
    import audiomp3
    import audioio

    audio = audioio.AudioOut(board.A0)

    mp3files = ["slow.mp3", "happy.mp3"]

    mp3 = open(mp3files[0], "rb")
    decoder = audiomp3.MP3Decoder(mp3)

    for filename in mp3files:
        decoder.file = open(filename, "rb")
        audio.play(decoder)
        print("Playing:", filename)
        while audio.playing:
            pass

The example content, as above, should contain NO commented out code, NO setup comment labels, and
NO other commented out setup code.
"""
import board
import audiomp3

# For most SAMD51 boards
import audioio

audio = audioio.AudioOut(board.A0)

# For most RP2040 and nRF boards
# import audiopwmio
#
# audio = audiopwmio.PWMAudioOut(board.A0)

# For MacroPad, Circuit Playground Bluefruit, and any RP2040 or nRF boards with a built-in speaker
# and requiring you to enable the SPEAKER_ENABLE pin
# import audiopwmio
# import digitalio
#
# shutdown = digitalio.DigitalInOut(board.SPEAKER_ENABLE)
# shutdown.switch_to_output(True)
# audio = audiopwmio.PWMAudioOut(board.SPEAKER)

# For any SAMD51 boards with a built in speaker and requiring you to enable the SPEAKER_ENABLE pin
# import audioio
# import digitalio
#
# shutdown = digitalio.DigitalInOut(board.SPEAKER_ENABLE)
# shutdown.switch_to_output(True)
# audio = audioio.AudioOut(board.SPEAKER)

# For CLUE or nRF boards with built-in speaker and no SPEAKER_ENABLE pin
# import audiopwmio
#
# audio = audiopwmio.PWMAudioOut(board.SPEAKER)

# For any SAMD51 boards with a built in speaker and no SPEAKER_ENABLE pin
# import audioio
#
# audio = audioio.AudioOut(board.SPEAKER)

mp3files = ["slow.mp3", "happy.mp3"]

mp3 = open(mp3files[0], "rb")
decoder = audiomp3.MP3Decoder(mp3)

for filename in mp3files:
    decoder.file = open(filename, "rb")
    audio.play(decoder)
    print("Playing:", filename)
    while audio.playing:
        pass

print("Done playing!")
