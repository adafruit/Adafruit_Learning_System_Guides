# SPDX-FileCopyrightText: 2023 Liz Clark for Adafruit Industries
#
# SPDX-License-Identifier: MIT

import os
import random
import board
import audiocore
import audiobusio
import audiomixer
import pwmio
from digitalio import DigitalInOut, Direction
import neopixel
from adafruit_motor import servo
from adafruit_ticks import ticks_ms, ticks_add, ticks_diff
from adafruit_led_animation.animation.pulse import Pulse
from adafruit_led_animation.color import RED, BLACK, GREEN
import adafruit_display_text.label
import displayio
import framebufferio
import rgbmatrix
import terminalio
import adafruit_vl53l4cd

distance_trigger = 90 # cm
text="Here lies Fred"
text_color = 0xff0000
# how often to check for a new trigger from ToF
pause_time = 30 # seconds
# speed for scrolling the text on the matrix
scroll_time = 0.1 # seconds

displayio.release_displays()

# enable external power pin
# provides power to the external components
external_power = DigitalInOut(board.EXTERNAL_POWER)
external_power.direction = Direction.OUTPUT
external_power.value = True

i2c = board.I2C()
vl53 = adafruit_vl53l4cd.VL53L4CD(i2c)

vl53.inter_measurement = 0
vl53.timing_budget = 200

matrix = rgbmatrix.RGBMatrix(
    width=64, height=32, bit_depth=4,
    rgb_pins=[board.D6, board.D5, board.D9, board.D11, board.D10, board.D12],
    addr_pins=[board.D25, board.D24, board.A3, board.A2],
    clock_pin=board.D13, latch_pin=board.D0, output_enable_pin=board.D1)

display = framebufferio.FramebufferDisplay(matrix, auto_refresh=True)

line1 = adafruit_display_text.label.Label(
    terminalio.FONT,
    color=text_color,
    text=text)
line1.x = 1
line1.y = 14

def scroll(line):
    line.x = line.x - 1
    line_width = line.bounding_box[2]
    if line.x < -line_width:
        line.x = display.width

g = displayio.Group()
g.append(line1)

display.root_group = g

wavs = []
for filename in os.listdir('/tomb_sounds'):
    if filename.lower().endswith('.wav') and not filename.startswith('.'):
        wavs.append("/tomb_sounds/"+filename)

audio = audiobusio.I2SOut(board.I2S_BIT_CLOCK, board.I2S_WORD_SELECT, board.I2S_DATA)
mixer = audiomixer.Mixer(voice_count=1, sample_rate=22050, channel_count=1,
                         bits_per_sample=16, samples_signed=True, buffer_size=32768)

mixer.voice[0].level = 1
audio.play(mixer)
wav_length = len(wavs) - 1

def open_audio(num):
    n = wavs[num]
    f = open(n, "rb")
    w = audiocore.WaveFile(f)
    return w

PIXEL_PIN = board.EXTERNAL_NEOPIXELS
BRIGHTNESS = 0.3
NUM_PIXELS = 2

PIXELS = neopixel.NeoPixel(PIXEL_PIN, NUM_PIXELS, auto_write=True)
pulse = Pulse(PIXELS, speed=0.05, color=RED, period=3)
COLORS = [RED, GREEN, BLACK]

SERVO_PIN = board.EXTERNAL_SERVO
PWM = pwmio.PWMOut(SERVO_PIN, duty_cycle=2 ** 15, frequency=50)
SERVO = servo.Servo(PWM)
SERVO.angle = 0

clock = ticks_ms()
the_time = 5000
x = 0
scroll_clock = ticks_ms()
scroll_time = int(scroll_time * 1000)
pause_clock = ticks_ms()
pause_time = pause_time * 1000
pause = False

vl53.start_ranging()

while True:

    vl53.clear_interrupt()

    if vl53.distance < distance_trigger:
        if not pause:
            print("Distance: {} cm".format(vl53.distance))
            SERVO.angle = 90
            wave = open_audio(random.randint(0, wav_length))
            mixer.voice[0].play(wave)
            while mixer.playing:
                pulse.color = COLORS[x]
                pulse.animate()
                if ticks_diff(ticks_ms(), scroll_clock) >= scroll_time:
                    scroll(line1)
                    display.refresh(minimum_frames_per_second=0)
                    scroll_clock = ticks_add(scroll_clock, scroll_time)
            x = (x + 1) % 2
            pause = True
            print("paused")
            pause_clock = ticks_add(pause_clock, pause_time)
        else:
            if ticks_diff(ticks_ms(), pause_clock) >= pause_time:
                print("back to sensing")
                pause = False
            print("still paused")
    if ticks_diff(ticks_ms(), scroll_clock) >= scroll_time:
        print("Distance: {} cm".format(vl53.distance))
        scroll(line1)
        display.refresh(minimum_frames_per_second=0)
        scroll_clock = ticks_add(scroll_clock, scroll_time)
    SERVO.angle = 0
    pulse.color = COLORS[2]
    pulse.animate()
