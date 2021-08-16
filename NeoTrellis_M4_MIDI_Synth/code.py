"""
NeoTrellis M4 Express MIDI synth

Adafruit invests time and resources providing this open source code.
Please support Adafruit and open source hardware by purchasing
products from Adafruit!

Written by Dave Astels for Adafruit Industries
Copyright (c) 2018 Adafruit Industries
Licensed under the MIT license.

All text above must be included in any redistribution.
"""

import os
import parser
import sequencer
import synth
import adafruit_trellism4

trellis = adafruit_trellism4.TrellisM4Express(rotation=0)
trellis.pixels.brightness = 0.1
trellis.pixels.fill(0)

syn = synth.Synth()
seq = sequencer.Sequencer(syn)
p = parser.MidiParser()

voices = sorted([f.split('.')[0] for f in os.listdir('/samples')
                 if f.endswith('.txt') and not f.startswith('.')])
print('Voices found: ', voices)
tunes = sorted([f for f in os.listdir('/midi')
                if f.endswith('.mid') and not f.startswith('.')])
print('Midi files found: ', tunes)

selected_voice = None

def reset_voice_buttons():
    for i in range(len(voices)):
        trellis.pixels[(i, 0)] = 0x0000FF

def reset_tune_buttons():
    for i in range(len(tunes)):
        trellis.pixels[(i % 8, (i // 8) + 1)] = 0x00FF00

current_press = set()
reset_voice_buttons()
reset_tune_buttons()

while True:
    pressed = set(trellis.pressed_keys)
    just_pressed = pressed - current_press
    for down in just_pressed:
        if down[1] == 0:
            if down[0] < len(voices):                  # a voice selection
                selected_voice = down[0]
                reset_voice_buttons()
                trellis.pixels[down] = 0xFFFFFF
                syn.voice = voices[selected_voice]
        else:
            tune_index = (down[1] - 1) * 8 + down[0]
            if tune_index < len(tunes) and selected_voice is not None:
                trellis.pixels[down] = 0xFFFFFF
                header, tracks = p.parse('/midi/' + tunes[tune_index])
                for track in tracks:
                    seq.play(track)
                reset_tune_buttons()

    current_press = pressed
