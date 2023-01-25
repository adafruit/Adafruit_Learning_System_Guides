# SPDX-FileCopyrightText: 2023 Liz Clark for Adafruit Industries
# SPDX-License-Identifier: MIT

import time
import board
import digitalio
import audiomixer
import audiomp3
from audiopwmio import PWMAudioOut as AudioOut
from adafruit_seesaw import seesaw, rotaryio, digitalio as seesaw_io, neopixel as seesaw_neopixel
from adafruit_led_animation.animation.pulse import Pulse
import neopixel

# wait a little bit so USB can stabilize and not glitch audio
time.sleep(3)

# enable propmaker speaker output
enable = digitalio.DigitalInOut(board.D10)
enable.direction = digitalio.Direction.OUTPUT
enable.value = True

# speaker pin on the propmaker
audio = AudioOut(board.A0)
# create mixer instance
mixer = audiomixer.Mixer(voice_count=1, sample_rate=22050, channel_count=1,
                         bits_per_sample=16, samples_signed=True)
# attach mixer to audio playback
audio.play(mixer)

# open mp3 audio file
audio_file = audiomp3.MP3Decoder(open("Enceladus_Hiss_NASA.mp3","rb"))
# play audio file in first channel of mixer
mixer.voice[0].play(audio_file, loop=True)
# set mixer channel level
mixer.voice[0].level = 0

# propmaker neopixel pin
pixel_pin = board.D5
num_pixels = 35

pixels = neopixel.NeoPixel(pixel_pin, num_pixels, brightness=0.3, auto_write=False)

# define neopixel colors
RED = (255, 0, 0)
BLUE = (0, 0, 255)

# pulse animation
pulse = Pulse(pixels, speed=0.1, color=RED, period=3)

# i2c setup for rp2040 feather stemma port
i2c = board.STEMMA_I2C()

# rotary encoder
enc0 = seesaw.Seesaw(i2c, addr=0x36)
encoder0 = rotaryio.IncrementalEncoder(enc0)
last_position0 = None

# encoder button
enc0.pin_mode(24, enc0.INPUT_PULLUP)
enc_button = seesaw_io.DigitalIO(enc0, 24)
enc_button_state = False

# encoder neopixel
pixel0 = seesaw_neopixel.NeoPixel(enc0, 6, 1)
pixel0.brightness = 0.2
pixel0.fill(BLUE)

# variables
volume = 0 # volume
pixel_level = 25 # pixel brightness for rings
last_pos0 = 0 # position of the encoder
ctrl_mode = 0 # control mode set with encoder

while True:
    # run neopixel animation
    pulse.animate()
    # get encoder position
    pos0 = -encoder0.position

    # if the encoder button is pressed..
    if not enc_button.value and not enc_button_state:
        enc_button_state = True
        # switch between control modes
        if ctrl_mode == 0:
            ctrl_mode = 1
        else:
            ctrl_mode = 0
        print("ctrl_mode is %d" % ctrl_mode)
    # button debounce
    if enc_button.value and enc_button_state:
        enc_button_state = False
    # if control mode is 0..
    # control the volume of the white noise
    if ctrl_mode == 0:
        # encoder neopixel is blue
        pixel0.fill(BLUE)
        # if the encoder moves..
        if pos0 != last_pos0:
            # if you increase the encoder
            # increase value by 0.1
            # maxed out at 1
            if pos0 > last_pos0:
                volume = volume + 0.1
                if volume > 1:
                    volume = 1
            # if you decrease
            # decrease value by 0.1
            # minimum value of 0
            if pos0 < last_pos0:
                volume = volume - 0.1
                if volume < 0:
                    volume = 0
            print(volume)
            # reset the position
            last_pos0 = pos0
    # if control mode is 1..
    # control the brightness of the neopixel rings
    # actually controlling the % of red, not brightness directly
    if ctrl_mode == 1:
        # set the encoder neopixel to red
        pixel0.fill(RED)
        # if you increase the encoder
        # increase value by 10
        # max out at 255
        if pos0 != last_pos0:
            if pos0 > last_pos0:
                pixel_level = pixel_level + 10
                if pixel_level > 255:
                    pixel_level = 255
            # if you decrease the encoder
            # decrease value by 10
            # minimum level of 25
            if pos0 < last_pos0:
                pixel_level = pixel_level - 10
                if pixel_level < 25:
                    pixel_level = 25
            print(pixel_level)
            # reset the position
            last_pos0 = pos0
    # set the neopixel ring color
    pulse.color = (pixel_level, 0, 0)
    # set the audio volume
    mixer.voice[0].level = volume
