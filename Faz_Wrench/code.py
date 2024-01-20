# SPDX-FileCopyrightText: Copyright (c) 2023 Liz Clark for Adafruit Industries
#
# SPDX-License-Identifier: MIT

import os
import random
import board
import audiocore
import audiobusio
import audiomixer
from digitalio import DigitalInOut, Direction
import neopixel
from adafruit_ticks import ticks_ms, ticks_add, ticks_diff
from adafruit_led_animation.animation.pulse import Pulse
from adafruit_led_animation.color import RED, GREEN
import adafruit_character_lcd.character_lcd_i2c as character_lcd
import adafruit_lis3dh
from adafruit_seesaw.seesaw import Seesaw
from adafruit_seesaw.rotaryio import IncrementalEncoder
import keypad

puzzle_time = 5 # seconds

lcd_columns = 16
lcd_rows = 2

# enable external power pin
# provides power to the external components
external_power = DigitalInOut(board.EXTERNAL_POWER)
external_power.direction = Direction.OUTPUT
external_power.value = True

i2c = board.I2C()

int1 = DigitalInOut(board.ACCELEROMETER_INTERRUPT)
lis3dh = adafruit_lis3dh.LIS3DH_I2C(i2c, int1=int1)
lis3dh.range = adafruit_lis3dh.RANGE_2_G

ss_enc0 = Seesaw(i2c, addr=0x36)
enc0 = IncrementalEncoder(ss_enc0)

button = keypad.Keys((board.EXTERNAL_BUTTON, board.D13,), value_when_pressed=False, pull=True)

lcd = character_lcd.Character_LCD_I2C(i2c, lcd_columns, lcd_rows)
lcd.backlight = True

puzzle_msgs = ["UNLOCK\nDOOR", "DOOR\nUNLOCKED", "UNLOCKING"]

wavs = []
for filename in os.listdir('/faz_sounds'):
    if filename.lower().endswith('.wav') and not filename.startswith('.'):
        wavs.append("/faz_sounds/"+filename)
wavs.sort()
print(wavs)

audio = audiobusio.I2SOut(board.I2S_BIT_CLOCK, board.I2S_WORD_SELECT, board.I2S_DATA)
mixer = audiomixer.Mixer(voice_count=1, sample_rate=22050, channel_count=1,
                         bits_per_sample=16, samples_signed=True, buffer_size=32768)
volume = 0.5
mixer.voice[0].level = volume
audio.play(mixer)
wav_length = len(wavs) - 1

def open_audio(num):
    n = wavs[num]
    f = open(n, "rb")
    w = audiocore.WaveFile(f)
    return w

PIXEL_PIN = board.EXTERNAL_NEOPIXELS
BRIGHTNESS = 0.3
NUM_PIXELS = 8

PIXELS = neopixel.NeoPixel(PIXEL_PIN, NUM_PIXELS, auto_write=True)
pulse = Pulse(PIXELS, speed=0.001, color=RED, period=3)

puzzle_clock = ticks_ms()
puzzle_time = puzzle_time * 1000

puzzle = False
wave = open_audio(0)
pos0 = volume
last_pos0 = pos0
node_num = 0

def normalize(val, min_v, max_v):
    return max(min(max_v, val), min_v)

def puzzle_string(length):
    _string = ""
    for _ in range(length/2):
        b = random.randint(0, 1)
        if b == 0:
            r = chr(random.randint(ord('A'), ord('Z')))
        else:
            r = str(random.randint(0, 9))
        _string += r
    _string += "\n"
    for _ in range(length/2):
        b = random.randint(0, 1)
        if b == 0:
            r = chr(random.randint(ord('A'), ord('Z')))
        else:
            r = str(random.randint(0, 9))
        _string += r
    lcd.message = _string
    return _string

while True:
    event = button.events.get()
    if event and event.pressed:
        number = event.key_number
        if number == 0 and not puzzle:
            pulse.fill(GREEN)
            puzzle = True
            lcd.clear()
            lcd.message = puzzle_msgs[2]
            wave = open_audio(1)
            mixer.voice[0].play(wave)
            while mixer.playing:
                pass
            puzzle_clock = ticks_add(ticks_ms(), puzzle_time)
        if number == 1:
            lcd.clear()
            node_num = (node_num + 1) % 5
            print(node_num)

    if puzzle:
        x, y, z = [
            value / adafruit_lis3dh.STANDARD_GRAVITY for value in lis3dh.acceleration
            ]
        puzzle_string(lcd_columns*lcd_rows)
        if z > 0:
            wave = open_audio(2)
            print("playing up")
            pulse.fill(GREEN)
        else:
            wave = open_audio(3)
            print("playing down")
            pulse.fill(RED)
        mixer.voice[0].play(wave)
        while mixer.playing:
            puzzle_string(lcd_columns*lcd_rows)
            x, y, z = [
            value / adafruit_lis3dh.STANDARD_GRAVITY for value in lis3dh.acceleration
            ]
            if z > 0:
                pulse.fill(GREEN)
            else:
                pulse.fill(RED)
            if ticks_diff(ticks_ms(), puzzle_clock) >= puzzle_time:
                lcd.clear()
                puzzle = False
                lcd.message = puzzle_msgs[1]
                wave = open_audio(4)
                mixer.voice[0].play(wave)
                while mixer.playing:
                    pass
                print("puzzle done")
                wave = open_audio(0)
                lcd.clear()
                pulse.fill(RED)

    if not puzzle:
        pulse.animate()
        mixer.voice[0].play(wave, loop=True)
        if node_num > 3:
            lcd.message = "SECURITY\nBREACHED"
        else:
            lcd.message = f"DEACTIVATED:\n{node_num} of 4"
        pos0 = -enc0.position
        if pos0 != last_pos0:
            if pos0 > last_pos0:
                volume = volume + 0.1
            else:
                volume = volume - 0.1
            volume = normalize(volume, 0.0, 1.0)
            mixer.voice[0].level = volume
            last_pos0 = pos0
