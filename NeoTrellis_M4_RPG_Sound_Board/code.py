"""
Tabletop RPG soundboard for the NeoTrellisM4

Adafruit invests time and resources providing this open source code.
Please support Adafruit and open source hardware by purchasing
products from Adafruit!

Written by Dave Astels for Adafruit Industries
Copyright (c) 2018 Adafruit Industries
Licensed under the MIT license.

All text above must be included in any redistribution.
"""

# pylint: disable=wildcard-import,unused-wildcard-import,eval-used

import time
import board
import audioio
import adafruit_trellism4
from color_names import *

# Our keypad + neopixel driver
trellis = adafruit_trellism4.TrellisM4Express(rotation=0)


SELECTED_COLOR = WHITE            # the color for the selected sample
SAMPLE_FOLDER = '/samples/'       # the name of the folder containing the samples
SAMPLES = []
BLACK = 0x000000


# load the sound & color specifications
with open('soundboard.txt', 'r') as f:
    for line in f:
        cleaned = line.strip()
        if len(cleaned) > 0 and cleaned[0] != '#':
            if cleaned == 'pass':
                SAMPLES.append(('does_not_exist.wav', BLACK))
            else:
                f_name, color = cleaned.split(',', 1)
                SAMPLES.append((f_name.strip(), eval(color.strip())))


# Parse the first file to figure out what format its in
channel_count = None
bits_per_sample = None
sample_rate = None
with open(SAMPLE_FOLDER+SAMPLES[0][0], 'rb') as f:
    wav = audioio.WaveFile(f)
    channel_count = wav.channel_count
    bits_per_sample = wav.bits_per_sample
    sample_rate = wav.sample_rate
    print('%d channels, %d bits per sample, %d Hz sample rate ' %
          (wav.channel_count, wav.bits_per_sample, wav.sample_rate))

    # Audio playback object - we'll go with either mono or stereo depending on
    # what we see in the first file
    if wav.channel_count == 1:
        audio = audioio.AudioOut(board.A1)
    elif wav.channel_count == 2:
        audio = audioio.AudioOut(board.A1, right_channel=board.A0)
    else:
        raise RuntimeError('Must be mono or stereo waves!')

mixer = audioio.Mixer(voice_count=2,
                      sample_rate=sample_rate,
                      channel_count=channel_count,
                      bits_per_sample=bits_per_sample,
                      samples_signed=True)
audio.play(mixer)

# Clear all pixels
trellis.pixels.fill(0)

# Light up button with a valid sound file attached
for i, v in enumerate(SAMPLES):
    filename = SAMPLE_FOLDER+v[0]
    try:
        with open(filename, 'rb') as f:
            wav = audioio.WaveFile(f)
            print(filename,
                  '%d channels, %d bits per sample, %d Hz sample rate ' %
                  (wav.channel_count, wav.bits_per_sample, wav.sample_rate))
            if wav.channel_count != channel_count:
                pass
            if wav.bits_per_sample != bits_per_sample:
                pass
            if wav.sample_rate != sample_rate:
                pass
            trellis.pixels[(i % 8, i // 8)] = v[1]
    except OSError:
        # File not found! skip to next
        pass


def stop_playing_sample(details):
    print('playing: ', details)
    mixer.stop_voice(details['voice'])
    trellis.pixels[details['neopixel_location']] = details['neopixel_color']
    details['file'].close()
    details['voice'] = None


current_press = set()
current_background = {'voice' : None}
currently_playing = {'voice' : None}
while True:
    pressed = set(trellis.pressed_keys)
    just_pressed = pressed - current_press
    # just_released = current_press - pressed

    for down in just_pressed:
        sample_num = down[1]*8 + down[0]
        try:
            filename = SAMPLE_FOLDER+SAMPLES[sample_num][0]
            f = open(filename, 'rb')
            wav = audioio.WaveFile(f)

            if down[1] == 0:              # background loop?
                if current_background['voice'] != None:
                    print('Interrupt')
                    stop_playing_sample(current_background)

                trellis.pixels[down] = WHITE
                mixer.play(wav, voice=0, loop=True)
                current_background = {
                    'voice': 0,
                    'neopixel_location': down,
                    'neopixel_color': SAMPLES[sample_num][1],
                    'sample_num': sample_num,
                    'file': f}
            else:
                if currently_playing['voice'] != None:
                    print('Interrupt')
                    stop_playing_sample(currently_playing)

                trellis.pixels[down] = WHITE
                mixer.play(wav, voice=1, loop=False)
                currently_playing = {
                    'voice': 1,
                    'neopixel_location': down,
                    'neopixel_color': SAMPLES[sample_num][1],
                    'sample_num': sample_num,
                    'file': f}
        except OSError:
            pass # File not found! skip to next

    # # check if any samples are done
    # # this currently doesn't work with the mixer until it supports per voice "is_playing" checking
    # if not audio.playing and currently_playing['voice'] != None:
    #     stop_playing_sample(currently_playing)

    time.sleep(0.01)  # a little delay here helps avoid debounce annoyances
    current_press = pressed
