# SPDX-FileCopyrightText: 2023 Liz Clark for Adafruit Industries
#
# SPDX-License-Identifier: MIT

import time
import random
import board
import audiocore
import audiobusio
import audiomixer
from digitalio import DigitalInOut, Direction
from adafruit_ticks import ticks_ms, ticks_add, ticks_diff
import neopixel
import adafruit_lis3dh

# CUSTOMIZE SENSITIVITY HERE: smaller numbers = more sensitive to motion
SWING_1_THRESHOLD = 130
SWING_2_THRESHOLD = 170

pixel_time = 10
Y_THRESHOLD = -9.0

fx_1 = audiocore.WaveFile(open("/sounds/swing1.wav", "rb"))
fx_2 = audiocore.WaveFile(open("/sounds/swing1b.wav", "rb"))
fx_3 = audiocore.WaveFile(open("/sounds/swing2.wav", "rb"))
fx_4 = audiocore.WaveFile(open("/sounds/swing3.wav", "rb"))

tracks = [fx_1, fx_2, fx_3, fx_4]
audio = audiobusio.I2SOut(board.I2S_BIT_CLOCK, board.I2S_WORD_SELECT, board.I2S_DATA)
mixer = audiomixer.Mixer(voice_count=3, sample_rate=22050, channel_count=1,
                         bits_per_sample=16, samples_signed=True)
audio.play(mixer)

# external neopixels
num_pixels = 50
pixels = neopixel.NeoPixel(board.EXTERNAL_NEOPIXELS, num_pixels, auto_write=False)
pixels.brightness = 0.2

# Gradient colors (start and end)
pale_green = (50, 255, 50)
yellow = (255, 255, 0)
# Pulse parameters
pulse_speed = 0.01  # Speed of the pulse (lower is slower)
brightness_step = 5  # Amount by which to step the brightness

# onboard LIS3DH
i2c = board.I2C()
int1 = DigitalInOut(board.ACCELEROMETER_INTERRUPT)
lis3dh = adafruit_lis3dh.LIS3DH_I2C(i2c, int1=int1)
# Accelerometer Range (can be 2_G, 4_G, 8_G, 16_G)
lis3dh.range = adafruit_lis3dh.RANGE_2_G

# enable external power pin
# provides power to the external components
external_power = DigitalInOut(board.EXTERNAL_POWER)
external_power.direction = Direction.OUTPUT
external_power.value = True

mode = 0
brightness = 0
increasing = True
pixel_clock = ticks_ms()
VERTICAL_TIME = 2.0  # Time in seconds the sensor needs to be vertical to trigger
# Variables to track time
vertical_start_time = None

while True:
    # default
    if mode == 0:
        if ticks_diff(ticks_ms(), pixel_clock) >= pixel_time:
            for i in range(num_pixels):
                # Calculate gradient between pale_green and yellow
                ratio = i / (num_pixels - 1)
                r = int((yellow[0] - pale_green[0]) * ratio + pale_green[0])
                g = int((yellow[1] - pale_green[1]) * ratio + pale_green[1])
                b = int((yellow[2] - pale_green[2]) * ratio + pale_green[2])

                # Adjust brightness by scaling the RGB values
                scaled_r = int(r * (brightness / 255))
                scaled_g = int(g * (brightness / 255))
                scaled_b = int(b * (brightness / 255))

                pixels[i] = scaled_r, scaled_g, scaled_b
            pixels.show()
            # Adjust brightness up and down
            if increasing:
                brightness += brightness_step
                if brightness >= 255:
                    brightness = 255
                    increasing = False
            else:
                brightness -= brightness_step
                if brightness <= 0:
                    brightness = 0
                    increasing = True
            pixel_clock = ticks_add(pixel_clock, pixel_time)
        x, y, z = lis3dh.acceleration
        #print(x, y, z)
        if abs(y) > Y_THRESHOLD and abs(x) < 2.0 and abs(z) < 2.0:
            if vertical_start_time is None:
                vertical_start_time = time.monotonic()  # Start timing
            elif time.monotonic() - vertical_start_time >= VERTICAL_TIME:
                print("vertical")
                mode = "vertical"
        else:
            vertical_start_time = None  # Reset if the sensor is not vertical
        accel_total = x * x + z * z
        if accel_total >= SWING_2_THRESHOLD:
            print("swing 2")
            mode = "swing 2"
        elif accel_total >= SWING_1_THRESHOLD:
            print("swing 1")
            mode = "swing 1"
    elif mode == "swing 1":
        mixer.voice[0].play(tracks[random.randint(0, 1)])
        while mixer.voice[0].playing:
            pixels.fill(pale_green)
            pixels.show()
        mode = 0
    # clash or move
    elif mode == "swing 2":
        mixer.voice[1].play(tracks[2])
        while mixer.voice[1].playing:
            pixels.fill(yellow)
            pixels.show()
        mode = 0
    elif mode == "vertical":
        mixer.voice[2].play(tracks[3])
        while mixer.voice[2].playing:
            pixels.fill(yellow)
            pixels.show()
        vertical_start_time = None
        mode = 0
