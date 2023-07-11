# SPDX-FileCopyrightText: 2023 Liz Clark for Adafruit Industries
#
# SPDX-License-Identifier: MIT

import os
import time
import random
import board
import audiocore
import audiobusio
import audiomixer
import pwmio
import neopixel
import adafruit_lis3dh
from random import randint
from adafruit_ticks import ticks_ms, ticks_add, ticks_diff
from digitalio import DigitalInOut, Direction, Pull
from adafruit_motor import servo
from adafruit_led_animation.animation.comet import Comet
from adafruit_led_animation.animation.pulse import Pulse
from adafruit_led_animation.animation.sparkle import Sparkle
from adafruit_led_animation.color import RED, BLUE, BLACK

# enable external power pin
# provides power to the external components
external_power = DigitalInOut(board.EXTERNAL_POWER)
external_power.direction = Direction.OUTPUT
external_power.value = True

i2c = board.I2C()
int1 = DigitalInOut(board.ACCELEROMETER_INTERRUPT)
lis3dh = adafruit_lis3dh.LIS3DH_I2C(i2c, int1=int1)
lis3dh.range = adafruit_lis3dh.RANGE_2_G

# Setup button switch
switch = DigitalInOut(board.EXTERNAL_BUTTON)
switch.direction = Direction.INPUT
switch.pull = Pull.UP
switch_state = False

wavs = []
for filename in os.listdir('/WAVs'):
    if filename.lower().endswith('.wav') and not filename.startswith('.'):
        wavs.append("/WAVs/"+filename)

audio = audiobusio.I2SOut(board.I2S_BIT_CLOCK, board.I2S_WORD_SELECT, board.I2S_DATA)
mixer = audiomixer.Mixer(voice_count=1, sample_rate=22050, channel_count=1,
                         bits_per_sample=16, samples_signed=True, buffer_size=32768)

mixer.voice[0].level = 1
track_number = 0
wav_filename = wavs[track_number]
wav_file = open(wav_filename, "rb")
wave = audiocore.WaveFile(wav_file)
audio.play(mixer)
mixer.voice[0].play(wave)

def open_audio(num):
    wav_filename = wavs[num]
    wav_file = open(wav_filename, "rb")
    wave = audiocore.WaveFile(wav_file)
    return wave

PIXEL_PIN = board.EXTERNAL_NEOPIXELS
SERVO_PIN = board.EXTERNAL_SERVO
NUM_PIXELS = 8
ORDER = neopixel.GRB
BRIGHTNESS = 0.3

# Initialize servo
PWM = pwmio.PWMOut(SERVO_PIN, duty_cycle=2 ** 15, frequency=50)
SERVO = servo.Servo(PWM)

# Initialize NeoPixels and animations
pixel = neopixel.NeoPixel(board.NEOPIXEL, 1)
pixel.brightness = 1

PIXELS = neopixel.NeoPixel(PIXEL_PIN, NUM_PIXELS, auto_write=False,
                           pixel_order=ORDER)
LARSON = Comet(PIXELS, bounce=True, speed=0.07,
               tail_length=NUM_PIXELS//2,
               color=(BLUE[0] * BRIGHTNESS,  # This is a little faster than
                      BLUE[1] * BRIGHTNESS,  # using the NeoPixel brightness
                      BLUE[2] * BRIGHTNESS)) # setting.
pulse = Pulse(PIXELS, speed=0.05,
                color=(BLUE[0] * BRIGHTNESS,  # This is a little faster than
                      BLUE[1] * BRIGHTNESS,  # using the NeoPixel brightness
                      BLUE[2] * BRIGHTNESS), period=3)
sparkle = Sparkle(PIXELS, speed=0.2,
                color=(RED[0] * BRIGHTNESS,  # This is a little faster than
                      RED[1] * BRIGHTNESS,  # using the NeoPixel brightness
                      RED[2] * BRIGHTNESS), num_sparkles=10)

SERVO.angle = POSITION = NEXT_POSITION = 90
MOVING = False                # Initial state = paused
START_TIME = ticks_ms() # Initial time
DURATION = 1000                # Hold initial position for 1 sec

adabot_talk = False

clock = ticks_ms()
prop_time = 1000
adabot_nap = False

mixer.voice[0].play(wave)
while mixer.playing:
    LARSON.animate()

while True: # Loop forever...
    if ticks_diff(ticks_ms(), clock) >= prop_time:
        x, y, z = [
        value / adafruit_lis3dh.STANDARD_GRAVITY for value in lis3dh.acceleration
        ]
        if z > 0.9:
            adabot_nap = True
            SERVO.angle = POSITION = NEXT_POSITION = 90
            pulse.color=(BLUE[0] * BRIGHTNESS,  # This is a little faster than
                          BLUE[1] * BRIGHTNESS,  # using the NeoPixel brightness
                          BLUE[2] * BRIGHTNESS)
        else:
            adabot_nap = False
            LARSON.color=(BLUE[0] * BRIGHTNESS,  # This is a little faster than
                          BLUE[1] * BRIGHTNESS,  # using the NeoPixel brightness
                          BLUE[2] * BRIGHTNESS)
        if not adabot_nap:
            MOVING = not MOVING
            if MOVING:             # Switching from paused to moving
                POSITION = NEXT_POSITION
                while abs(POSITION - NEXT_POSITION) < 10:  # Min +/- 10 degrees
                    NEXT_POSITION = random.uniform(0, 180) # Try, try again
                DURATION = 0.2 + 0.6 * abs(POSITION - NEXT_POSITION) / 180
            else:                  # Switching from moving to paused
                SERVO.angle = NEXT_POSITION         # Move to end of sweep
                DURATION = random.uniform(0.5, 2.5) # Pause time
        clock = ticks_add(clock, prop_time)
    if MOVING:
        FRACTION = 0.0 / DURATION                        # Linear 0 to 1
        FRACTION = (3 * FRACTION ** 2) - (2 * FRACTION ** 3) # Ease in/out
        SERVO.angle = POSITION + (NEXT_POSITION - POSITION) * FRACTION
    if adabot_talk:
        wave = open_audio(randint(1, 17))
        mixer.voice[0].play(wave)
        while mixer.playing:
            sparkle.animate()
        else:
            adabot_talk = False
            PIXELS.fill(BLACK)
            PIXELS.show()
    elif adabot_nap:
        pulse.animate()
    else:
        LARSON.animate()

    if not switch.value and switch_state is False:
        PIXELS.fill(BLACK)
        PIXELS.show()
        adabot_talk = True
        switch_state = True
    if switch.value and switch_state is True:
        switch_state = False
