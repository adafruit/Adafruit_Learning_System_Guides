# SPDX-FileCopyrightText: 2024 Noe Ruiz for Adafruit Industries
#
# SPDX-License-Identifier: MIT

import board
import audiocore
import audiobusio
import audiomixer
from digitalio import DigitalInOut, Direction
import pwmio
import neopixel
from adafruit_led_animation.animation.rainbow import Rainbow
from adafruit_motor import servo

# enable external power pin
# provides power to the external components
external_power = DigitalInOut(board.EXTERNAL_POWER)
external_power.direction = Direction.OUTPUT
external_power.value = True

# i2s playback
wave_file = open("carousel-loop.wav", "rb")
wave = audiocore.WaveFile(wave_file)
audio = audiobusio.I2SOut(board.I2S_BIT_CLOCK, board.I2S_WORD_SELECT, board.I2S_DATA)
mixer = audiomixer.Mixer(voice_count=1, sample_rate=22050, channel_count=1,
                         bits_per_sample=16, samples_signed=True)
audio.play(mixer)
mixer.voice[0].play(wave, loop=True)

# servo control
pwm = pwmio.PWMOut(board.EXTERNAL_SERVO, frequency=5)
prop_servo = servo.ContinuousServo(pwm)

# external neopixels
num_pixels = 43
pixels = neopixel.NeoPixel(board.EXTERNAL_NEOPIXELS, num_pixels)
pixels.brightness = 0.3
rainbow = Rainbow(pixels, speed=0.05, period=2)

while True:
    prop_servo.throttle = 1
    rainbow.animate()
    mixer.voice[0].level = 1
