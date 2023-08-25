# SPDX-FileCopyrightText: 2023 Liz Clark for Adafruit Industries
#
# SPDX-License-Identifier: MIT

import os
import time
import board
import audiocore
import audiobusio
import audiomixer
import adafruit_ds3231
from digitalio import DigitalInOut, Direction
import neopixel
import keypad

# enable external power pin
# provides power to the external components
external_power = DigitalInOut(board.EXTERNAL_POWER)
external_power.direction = Direction.OUTPUT
external_power.value = True

# setup external button pin as a keypad object
key = keypad.Keys((board.EXTERNAL_BUTTON,), value_when_pressed=False, pull=True)

# neopixel mouth setup
pixels = neopixel.NeoPixel(board.EXTERNAL_NEOPIXELS, 8, auto_write=True, brightness=0.2)
blue = (0, 0, 255)
off = (0, 0, 0)
pixels.fill(off)

# rtc module
i2c = board.I2C()
rtc = adafruit_ds3231.DS3231(i2c)

# pylint: disable-msg=using-constant-test
if False:  # change to True if you want to set the time!
    #                     year, mon, date, hour, min, sec, wday, yday, isdst
    t = time.struct_time((2023, 8, 22, 16, 47, 00, 1, -1, -1))
    # you must set year, mon, date, hour, min, sec and weekday
    # yearday is not supported, isdst can be set but we don't do anything with it at this time
    print("Setting time to:", t)  # uncomment for debugging
    rtc.datetime = t
    print()
# pylint: enable-msg=using-constant-test

# sound arrays
bookend_sounds = []
hour_sounds = []
min_sounds = []
clock_queue = []
# bring in the audio files and put them into the different arrays
for filename in os.listdir('/clock_sounds'):
    if filename.lower().endswith('.wav') and not filename.startswith('.'):
        if filename.startswith('h'):
            hour_sounds.append("/clock_sounds/"+filename)
        elif filename.startswith('m'):
            min_sounds.append("/clock_sounds/"+filename)
        else:
            bookend_sounds.append("/clock_sounds/"+filename)
# sort the arrays alphabetically
bookend_sounds.sort()
hour_sounds.sort()
min_sounds.sort()
print(hour_sounds)
print(min_sounds)
print(bookend_sounds)

# i2s amp setup with mixer
audio = audiobusio.I2SOut(board.I2S_BIT_CLOCK, board.I2S_WORD_SELECT, board.I2S_DATA)
mixer = audiomixer.Mixer(voice_count=1, sample_rate=22050, channel_count=1,
                         bits_per_sample=16, samples_signed=True)
audio.play(mixer)
mixer.voice[0].level = 0.5

# function for queueing wave files
def open_audio(wavs, num):
    n = wavs[num]
    f = open(n, "rb")
    w = audiocore.WaveFile(f)
    clock_queue.append(w)
    return w

# queue boot up sound to play before going into the loop
boot_sound = open_audio(bookend_sounds, 2)

# function for gathering clock audio files
def prep_clock(hour_num, minute_num):
    # queues "the time is.."
    open_audio(bookend_sounds, 1)
    # convert 24 hour time from RTC to 12 hour
    if hour_num >= 12:
        # convert 24 hour to 12 hour
        if hour_num > 12:
            hour_num = hour_num - 12
        # set to PM
        ampm_num = 3
    # otherwise its the morning
    else:
        # set AM
        ampm_num = 0
    # queueing hour, single digit waves have a 0 before the number
    if hour_num <= 9:
        print(hour_num)
        h = hour_sounds.index(f'/clock_sounds/h0{hour_num}.wav')
    else:
        print(hour_num)
        h = hour_sounds.index(f'/clock_sounds/h{hour_num}.wav')
    # open wave file for the hour
    open_audio(hour_sounds, h)
    # if the minute is divisible by 10 (10, 20, 30, etc)
    if minute_num % 10 == 0:
        # check for on the hour (1:00, 2:00, etc)
        if minute_num == 0:
            m = min_sounds.index(f'/clock_sounds/m{minute_num}0.wav')
        else:
            m = min_sounds.index(f'/clock_sounds/m{minute_num}.wav')
        print(minute_num)
    # individual wave files exist for 1-19
    elif minute_num <= 19:
        print(minute_num)
        # if it's a single digit number, bring in the "oh" wave file
        if minute_num <= 9:
            mm = min_sounds.index('/clock_sounds/m0x.wav')
            open_audio(min_sounds, mm)
        m = min_sounds.index(f'/clock_sounds/m{minute_num}.wav')
    # otherwise, for minutes 21-59 that are not divisible by 10
    else:
        # we need to seperate the minutes digits
        digits = list(map(int, str(minute_num)))
        #print(digits)
        # get the tens spot (30, 40, etc)
        mm = min_sounds.index(f'/clock_sounds/m{digits[0]}x.wav')
        # add the wav to the array
        open_audio(min_sounds, mm)
        # get the ones spot (1, 2, etc)
        m = min_sounds.index(f'/clock_sounds/m{digits[1]}.wav')
        # combined it will say ex: "30...5"
    # add the wav to the array
    open_audio(min_sounds, m)
    # finish with am or pm
    open_audio(bookend_sounds, ampm_num)
# initial RTC read
t = rtc.datetime
print(t)
# say the time on boot
pixels.fill(blue)
prep_clock(t.tm_hour, t.tm_min)
for i in range(len(clock_queue)):
    mixer.voice[0].play(clock_queue[i], loop=False)
    while mixer.playing:
        pass
# clear the audio file queue
clock_queue.clear()
pixels.fill(off)

while True:
    # listen for button input
    event = key.events.get()
    if event:
        # if the button is pressed
        if event.pressed:
            # read from RTC module
            t = rtc.datetime
            # turn on neopixels
            pixels.fill(blue)
            # gather the audio files based on RTC reading
            prep_clock(t.tm_hour, t.tm_min)
            # play through each wave one by one
            for i in range(len(clock_queue)):
                mixer.voice[0].play(clock_queue[i], loop=False)
                while mixer.playing:
                    pass
            # afterwards clear out the queue
            clock_queue.clear()
            # turn off neopixels
            pixels.fill(off)
