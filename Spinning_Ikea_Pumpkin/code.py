# SPDX-FileCopyrightText: Copyright (c) 2024 Liz Clark for Adafruit Industries
#
# SPDX-License-Identifier: MIT

import time
import microncontroller
import board
import audiocore
import audiobusio
import audiomixer
import pwmio
from digitalio import DigitalInOut, Direction, Pull
from adafruit_ticks import ticks_ms, ticks_add, ticks_diff
from adafruit_motor import servo
import adafruit_vl53l1x

distance_delay = 4 # how often vl53 is read
servo_delays = [2.0, 1.5, 1.0, 0.5] # servo spin delay
distances = [150, 100, 80, 40] # in centimeters
max_audio = 1
# audio files
music = audiocore.WaveFile(open("music-loop-1.wav", "rb"))
fx_1 = audiocore.WaveFile(open("happy-halloween.wav", "rb"))
fx_2 = audiocore.WaveFile(open("laugh-2.wav", "rb"))
fx_3 = audiocore.WaveFile(open("laugh-3.wav", "rb"))

i2c = board.STEMMA_I2C()
vl53 = adafruit_vl53l1x.VL53L1X(i2c)

tracks = [music, fx_1, fx_2, fx_3]
audio = audiobusio.I2SOut(board.I2S_BIT_CLOCK, board.I2S_WORD_SELECT, board.I2S_DATA)
mixer = audiomixer.Mixer(voice_count=4, sample_rate=22050, channel_count=1,
                         bits_per_sample=16, samples_signed=True)
audio.play(mixer)
mixer.voice[0].play(tracks[0], loop=True)
mixer.voice[0].level = 0.0

# enable external power pin
# provides power to the external components
external_power = DigitalInOut(board.EXTERNAL_POWER)
external_power.direction = Direction.OUTPUT
external_power.value = True

switch = DigitalInOut(board.EXTERNAL_BUTTON)
switch.direction = Direction.INPUT
switch.pull = Pull.UP

# servo control
pwm = pwmio.PWMOut(board.EXTERNAL_SERVO, duty_cycle=2 ** 15, frequency=50)
servo = servo.ContinuousServo(pwm, min_pulse=750, max_pulse=2250)

vl53.start_ranging()

vl53_clock = ticks_ms()
vl53_time = distance_delay * 1000
servo_clock = ticks_ms()
servo_time = int(servo_delays[0] * 1000)
prop_time = False
servo_throttle = 0

while True:
    try:
        if switch.value:
            external_power.value = True
            if prop_time:
                if ticks_diff(ticks_ms(), servo_clock) >= servo_time:
                    print(servo_throttle)
                    servo.throttle = servo_throttle
                    servo_throttle = not servo_throttle
                    servo_clock = ticks_add(servo_clock, servo_time)
            if ticks_diff(ticks_ms(), vl53_clock) >= vl53_time:
                if vl53.data_ready:
                    print(f"Distance: {vl53.distance} cm")
                    vl53.clear_interrupt()
                if vl53.distance is None:
                    prop_time = False
                    mixer.voice[0].level = 0.0
                    servo_time = int(servo_delays[0] * 1000)
                    servo.throttle = 1.0
                else:
                    closest_distance = min(distances, key=lambda x: abs(vl53.distance - x))
                    # print(closest_distance)
                    if vl53.distance <= distances[0]:
                        prop_time = True
                        mixer.voice[0].level = max_audio
                    else:
                        prop_time = False
                        mixer.voice[0].level = 0.0
                        servo.throttle = 1.0
                    if closest_distance == distances[1]:
                        mixer.voice[1].play(tracks[1], loop=False)
                        servo_time = int(servo_delays[1] * 1000)
                    elif closest_distance == distances[2]:
                        mixer.voice[2].play(tracks[2], loop=False)
                        servo_time = int(servo_delays[2] * 1000)
                    elif closest_distance == distances[3]:
                        mixer.voice[3].play(tracks[3], loop=False)
                        servo_time = int(servo_delays[3] * 1000)
                vl53_clock = ticks_add(vl53_clock, vl53_time)
        else:
            external_power.value = False
    except Exception as error: # pylint: disable=broad-except
        print(error)
        time.sleep(5)
        microncontroller.reset()
