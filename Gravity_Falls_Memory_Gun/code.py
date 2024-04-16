# SPDX-FileCopyrightText: Copyright (c) 2024 Liz Clark for Adafruit Industries
#
# SPDX-License-Identifier: MIT

import os
import board
import audiocore
import audiobusio
from digitalio import DigitalInOut, Direction
import displayio
from adafruit_bitmap_font import bitmap_font
from adafruit_display_text import label
import adafruit_displayio_ssd1306
from adafruit_seesaw import seesaw, rotaryio
import vectorio
import keypad

#display setup
displayio.release_displays()
# enable external power pin
# provides power to the external components
external_power = DigitalInOut(board.EXTERNAL_POWER)
external_power.direction = Direction.OUTPUT
external_power.value = False

# rotary encoder
i2c = board.STEMMA_I2C()
seesaw = seesaw.Seesaw(i2c, addr=0x36)
encoder = rotaryio.IncrementalEncoder(seesaw)
last_position = 0

# oled
oled_reset = board.D9
display_bus = displayio.I2CDisplay(i2c, device_address=0x3D, reset=oled_reset)
WIDTH = 128
HEIGHT = 64
display = adafruit_displayio_ssd1306.SSD1306(display_bus, width=WIDTH, height=HEIGHT)

# trigger button
switch = keypad.Keys((board.EXTERNAL_BUTTON,), value_when_pressed=False, pull=True)

# audio!
wavs = []
wav_names = []
for filename in os.listdir('/wavs'):
    if filename.lower().endswith('.wav') and not filename.startswith('.'):
        wavs.append("/wavs/"+filename)
        wav_names.append(filename.replace('.wav', ''))
audio = audiobusio.I2SOut(board.I2S_BIT_CLOCK, board.I2S_WORD_SELECT, board.I2S_DATA)
num_wavs = len(wavs)
wav_index = 0
# function to open and play the audio files
def open_audio(num):
    n = wavs[num]
    f = open(n, "rb")
    w = audiocore.WaveFile(f)
    return w
wave = open_audio(wav_index)
audio.play(wave)

# make the display context
splash = displayio.Group()
display.root_group = splash
palette = displayio.Palette(1)
palette[0] = 0xFFFFFF
rect = vectorio.Rectangle(pixel_shader=palette, width=display.width, height=23, x=6, y=21)
splash.append(rect)
font = bitmap_font.load_font("/Arial-14.bdf")
color = 0xFFFFFF
text_0 = wav_names[(wav_index - 1) % num_wavs]
text_area_top_left = label.Label(font, text=text_0, color=color)
text_area_top_left.anchor_point = (0.0, 0.0)
text_area_top_left.anchored_position = (6, 0)
splash.append(text_area_top_left)

text_1 = wav_names[wav_index]
text_area_middle_left = label.Label(font, text=text_1,color=0x000000)
text_area_middle_left.anchor_point = (0.0, 0.5)
text_area_middle_left.anchored_position = (6, display.height / 2)
splash.append(text_area_middle_left)

text_2 = wav_names[(wav_index+1) % num_wavs]
text_area_bottom_left = label.Label(font, text=text_2, color=color)
text_area_bottom_left.anchor_point = (0.0, 1.0)
text_area_bottom_left.anchored_position = (6, display.height)
splash.append(text_area_bottom_left)

while True:

    event = switch.events.get()
    position = encoder.position
    if position != last_position:
        if position > last_position:
            wav_index = (wav_index + 1) % num_wavs
        else:
            wav_index = (wav_index - 1) % num_wavs
        text_area_top_left.text = wav_names[(wav_index-1) % num_wavs]
        text_area_middle_left.text = wav_names[wav_index]
        text_area_bottom_left.text = wav_names[(wav_index+1) % num_wavs]
        last_position = position
    if event:
        if event.pressed:
            external_power.value = True
            wave = open_audio(wav_index)
            audio.play(wave)
        if event.released:
            external_power.value = False
