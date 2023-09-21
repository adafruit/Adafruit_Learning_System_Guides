# SPDX-FileCopyrightText: 2022 Noe Ruiz for Adafruit Industries
# SPDX-License-Identifier: MIT
# Magic Band Reader with Wiz Kit RFID
import random
import board
import digitalio
import audiobusio
from audiocore import WaveFile
import neopixel
from adafruit_led_animation.animation.chase import Chase
from adafruit_led_animation.animation.solid import Solid
from adafruit_led_animation.color import (
    GREEN,
    BLACK,
)

# Setup button switch
button = digitalio.DigitalInOut(board.A1)
button.switch_to_input(pull=digitalio.Pull.DOWN)

# LRC is word_select, BCLK is bit_clock, DIN is data_pin.
# Feather RP2040
audio = audiobusio.I2SOut(bit_clock=board.D24, word_select=board.D25, data=board.A3)

# Make the neopixel object
pixels = neopixel.NeoPixel(board.D6, 24, brightness=.4)

# Setup the LED animations
chase = Chase(pixels, speed=0.02, color=GREEN, size=4, spacing=24)
solid = Solid(pixels, color=BLACK)

#Fuction for playing audio
def play_wav(name):
    print("playing", name)
    wave_file = open('sounds/' + name + '.wav', 'rb')
    wave = WaveFile(wave_file)
    audio.play(wave)

#List of audio files
sounds = [
    'chime',
    'excellent',
    'foolish',
    'hello',
    'operational',
    'startours'
]
while True:
    print("Waiting for button press to continue!")
    while not button.value:
        solid.animate()
    play_wav(random.choice(sounds))
    while audio.playing:
        chase.animate()
    print("Done!")
