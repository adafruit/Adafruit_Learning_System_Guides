# SPDX-FileCopyrightText: 2023 Liz Clark for Adafruit Industries
#
# SPDX-License-Identifier: MIT

import time
import board
import audiocore
import audiobusio
import audiomixer
import pwmio
from digitalio import DigitalInOut, Direction
from adafruit_ticks import ticks_ms, ticks_add, ticks_diff
from adafruit_motor import servo
import adafruit_lis3dh

time.sleep(2)

# enable external power pin
# provides power to the external components
external_power = DigitalInOut(board.EXTERNAL_POWER)
external_power.direction = Direction.OUTPUT
external_power.value = True

# i2s playback
wave_file = open("dune_thumper_sfx.wav", "rb")
wave = audiocore.WaveFile(wave_file)
audio = audiobusio.I2SOut(board.I2S_BIT_CLOCK, board.I2S_WORD_SELECT, board.I2S_DATA)
mixer = audiomixer.Mixer(voice_count=1, sample_rate=22050, channel_count=1,
                         bits_per_sample=16, samples_signed=True)
audio.play(mixer)
mixer.voice[0].play(wave, loop=True)
mixer.voice[0].level = 0

# servo control
pwm = pwmio.PWMOut(board.EXTERNAL_SERVO, frequency=10)
prop_servo = servo.ContinuousServo(pwm)
servo_move = False

i2c = board.I2C()
int1 = DigitalInOut(board.ACCELEROMETER_INTERRUPT)
lis3dh = adafruit_lis3dh.LIS3DH_I2C(i2c, int1=int1)
lis3dh.range = adafruit_lis3dh.RANGE_2_G

clock = ticks_ms()
prop_time = 4000

while True:
    if not servo_move:
        mixer.voice[0].level = 0.0
        prop_servo.throttle = 0.0
    else:
        prop_servo.throttle = 0.5
        mixer.voice[0].level = 0.5
        if ticks_diff(ticks_ms(), clock) >= prop_time:
            servo_move = False
    if lis3dh.shake(shake_threshold=20):
        servo_move = True
        clock = ticks_ms()
        clock = ticks_add(clock, prop_time)
