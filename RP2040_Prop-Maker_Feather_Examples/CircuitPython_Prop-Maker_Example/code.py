# SPDX-FileCopyrightText: 2023 Liz Clark for Adafruit Industries
#
# SPDX-License-Identifier: MIT

'''RP2040 Prop-Maker Feather Example'''

import time
import board
import audiocore
import audiobusio
import audiomixer
import pwmio
from digitalio import DigitalInOut, Direction, Pull
import neopixel
from adafruit_led_animation.animation.rainbow import Rainbow
from adafruit_motor import servo
import adafruit_lis3dh

# enable external power pin
# provides power to the external components
external_power = DigitalInOut(board.EXTERNAL_POWER)
external_power.direction = Direction.OUTPUT
external_power.value = True

# i2s playback
wave_file = open("StreetChicken.wav", "rb")
wave = audiocore.WaveFile(wave_file)
audio = audiobusio.I2SOut(board.I2S_BIT_CLOCK, board.I2S_WORD_SELECT, board.I2S_DATA)
mixer = audiomixer.Mixer(voice_count=1, sample_rate=22050, channel_count=1,
                         bits_per_sample=16, samples_signed=True)
audio.play(mixer)
mixer.voice[0].play(wave, loop=True)
mixer.voice[0].level = 0.5

# servo control
pwm = pwmio.PWMOut(board.EXTERNAL_SERVO, duty_cycle=2 ** 15, frequency=50)
prop_servo = servo.Servo(pwm)
angle = 0
angle_plus = True

# external button
switch = DigitalInOut(board.EXTERNAL_BUTTON)
switch.direction = Direction.INPUT
switch.pull = Pull.UP
switch_state = False

# external neopixels
num_pixels = 30
pixels = neopixel.NeoPixel(board.EXTERNAL_NEOPIXELS, num_pixels)
pixels.brightness = 0.3
rainbow = Rainbow(pixels, speed=0.05, period=2)

# onboard LIS3DH
i2c = board.I2C()
int1 = DigitalInOut(board.ACCELEROMETER_INTERRUPT)
lis3dh = adafruit_lis3dh.LIS3DH_I2C(i2c, int1=int1)
lis3dh.range = adafruit_lis3dh.RANGE_2_G

while True:
    # rainbow animation on external neopixels
    rainbow.animate()
    # read and print LIS3DH values
    x, y, z = [
        value / adafruit_lis3dh.STANDARD_GRAVITY for value in lis3dh.acceleration
    ]
    print(f"x = {x:.3f} G, y = {y:.3f} G, z = {z:.3f} G")
    # move servo back and forth
    prop_servo.angle = angle
    if angle_plus:
        angle += 5
    else:
        angle -= 5
    if angle == 180:
        angle_plus = False
    elif angle == 0:
        angle_plus = True
    # if the switched is pressed, turn off power to external components
    if not switch.value and switch_state is False:
        external_power.value = False
        switch_state = True
    if switch.value and switch_state is True:
        external_power.value = True
        switch_state = False

    time.sleep(0.02)
