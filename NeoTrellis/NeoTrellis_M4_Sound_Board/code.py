# SPDX-FileCopyrightText: 2018 Limor Fried for Adafruit Industries
#
# SPDX-License-Identifier: MIT

import time
import board
import audioio
import audiocore
import adafruit_fancyled.adafruit_fancyled as fancy
import adafruit_trellism4
from color_names import * # pylint: disable=wildcard-import,unused-wildcard-import


PLAY_SAMPLES_ON_START = False

SAMPLE_FOLDER = "/startrek/"  # the name of the folder containing the samples
# This soundboard can select up to *32* sound clips! each one has a filename
# which will be inside the SAMPLE_FOLDER above, and a *color* in a tuple ()
SAMPLES = [("01.wav", RED),
           ("02.wav", ORANGE),
           ("03.wav", YELLOW),
           ("04.wav", GREEN),
           ("05.wav", TEAL),
           ("06.wav", BLUE),
           ("07.wav", PURPLE),
           ("08.wav", PINK),
           ("09.wav", RED),
           ("10.wav", ORANGE),
           ("11.wav", YELLOW),
           ("12.wav", GREEN),
           ("13.wav", TEAL),
           ("14.wav", BLUE),
           ("15.wav", PURPLE),
           ("16.wav", PINK),
           ("17.wav", RED),
           ("18.wav", ORANGE),
           ("19.wav", YELLOW),
           ("20.wav", GREEN),
           ("21.wav", TEAL),
           ("22.wav", BLUE),
           ("23.wav", PURPLE),
           ("24.wav", PINK),
           ("25.wav", RED),
           ("26.wav", ORANGE),
           ("27.wav", YELLOW),
           ("28.wav", GREEN),
           ("29.wav", TEAL),
           ("30.wav", BLUE),
           ("31.wav", PURPLE),
           ("32.wav", PINK)]

# For the intro, pick any number of colors to make a fancy gradient!
INTRO_SWIRL = [RED, GREEN, BLUE]
# the color for the selected sample
SELECTED_COLOR = WHITE

# Our keypad + neopixel driver
trellis = adafruit_trellism4.TrellisM4Express(rotation=0)

# Play the welcome wav (if its there)
with audioio.AudioOut(board.A1, right_channel=board.A0) as audio:
    try:
        f = open("welcome.wav", "rb")
        wave = audiocore.WaveFile(f)
        audio.play(wave)
        swirl = 0  # we'll swirl through the colors in the gradient
        while audio.playing:
            for i in range(32):
                palette_index = ((swirl+i) % 32) / 32
                color = fancy.palette_lookup(INTRO_SWIRL, palette_index)
                # display it!
                trellis.pixels[(i%8, i//8)] = color.pack()
            swirl += 1
            time.sleep(0.005)
        f.close()
        # Clear all pixels
        trellis.pixels.fill(0)
        # just hold a moment
        time.sleep(0.5)
    except OSError:
        # no biggie, they probably deleted it
        pass

# Parse the first file to figure out what format its in
channel_count = None
bits_per_sample = None
sample_rate = None
with open(SAMPLE_FOLDER+SAMPLES[0][0], "rb") as f:
    wav = audiocore.WaveFile(f)
    print("%d channels, %d bits per sample, %d Hz sample rate " %
          (wav.channel_count, wav.bits_per_sample, wav.sample_rate))

    # Audio playback object - we'll go with either mono or stereo depending on
    # what we see in the first file
    if wav.channel_count == 1:
        audio = audioio.AudioOut(board.A1)
    elif wav.channel_count == 2:
        audio = audioio.AudioOut(board.A1, right_channel=board.A0)
    else:
        raise RuntimeError("Must be mono or stereo waves!")

# Clear all pixels
trellis.pixels.fill(0)

# turn on maybe play all of the buttons
for i, v in enumerate(SAMPLES):
    filename = SAMPLE_FOLDER+v[0]
    try:
        with open(filename, "rb") as f:
            wav = audiocore.WaveFile(f)
            print(filename,
                  "%d channels, %d bits per sample, %d Hz sample rate " %
                  (wav.channel_count, wav.bits_per_sample, wav.sample_rate))
            if wav.channel_count != channel_count:
                pass
            if wav.bits_per_sample != bits_per_sample:
                pass
            if wav.sample_rate != sample_rate:
                pass
            trellis.pixels[(i%8, i//8)] = v[1]
            if PLAY_SAMPLES_ON_START:
                audio.play(wav)
                while audio.playing:
                    pass
    except OSError:
        # File not found! skip to next
        pass

def stop_playing_sample(playback_details):
    print("playing: ", playback_details)
    audio.stop()
    trellis.pixels[playback_details['neopixel_location']] = playback_details['neopixel_color']
    playback_details['file'].close()
    playback_details['voice'] = None

current_press = set()
currently_playing = {'voice' : None}
last_samplenum = None
while True:
    pressed = set(trellis.pressed_keys)
    #if pressed:
    #    print("Pressed:", pressed)

    just_pressed = pressed - current_press
    just_released = current_press - pressed

    #if just_pressed:
    #    print("Just pressed", just_pressed)
    for down in just_pressed:
        sample_num = down[1]*8 + down[0]
        print(sample_num)
        try:
            filename = SAMPLE_FOLDER+SAMPLES[sample_num][0]
            f = open(filename, "rb")
            wav = audiocore.WaveFile(f)

            # is something else playing? interrupt it!
            if currently_playing['voice'] != None:
                print("Interrupt")
                stop_playing_sample(currently_playing)

            trellis.pixels[down] = WHITE
            audio.play(wav)
            # voice, neopixel tuple, color, and sample, file handle
            currently_playing = {
                'voice': 0,
                'neopixel_location': down,
                'neopixel_color': SAMPLES[sample_num][1],
                'sample_num': sample_num,
                'file': f}
        except OSError:
            pass # File not found! skip to next

    #if just_released:
    #    print("Just released:", just_released)

    # check if any samples are done
    if not audio.playing and currently_playing['voice'] != None:
        stop_playing_sample(currently_playing)

    time.sleep(0.01)  # a little delay here helps avoid debounce annoyances
    current_press = pressed
