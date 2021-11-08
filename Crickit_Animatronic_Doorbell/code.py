# SPDX-FileCopyrightText: 2021 John Park for Adafruit Industries
# SPDX-License-Identifier: MIT
import time
import random
import board
import audiomp3
import audiopwmio
from adafruit_crickit import crickit

ss = crickit.seesaw  # Crickit seesaw setup

button = crickit.SIGNAL1  # momentary switch to trigger animation
ss.pin_mode(button, ss.INPUT_PULLUP)

LED = crickit.SIGNAL4  # standard LED for eyeball lighting
ss.pin_mode(LED, ss.OUTPUT)

attract_switch = crickit.SIGNAL8  # attract mode switch or jumper
ss.pin_mode(attract_switch, ss.INPUT_PULLUP)

audio = audiopwmio.PWMAudioOut(board.A0)  # Feather outputs this pin to Crickit amplifier
audio_files = [  # use your own mono .mp3 files
               "phrase_01.mp3",
               "phrase_02.mp3",
               "phrase_03.mp3"
]
current_audio_file = 0

# two motors
motor_eye = crickit.dc_motor_1
motor_lid = crickit.dc_motor_2

def open_lid():
    motor_lid.throttle = 1  # full speed open
    time.sleep(0.25)
    motor_lid.throttle = 0  # hold

def close_lid():
    motor_lid.throttle = -1  # full speed closed
    time.sleep(0.25)
    motor_lid.throttle = 0

def blink(times):
    for _ in range(times):
        ss.digital_write(LED, True)
        time.sleep(0.1)
        ss.digital_write(LED, False)
        time.sleep(0.1)

def eye_look():
    motor_eye.throttle = random.uniform(0.6, 1.0)
    time.sleep(random.random())  # 0 to 1.0 seconds
    motor_eye.throttle = 0
    time.sleep(random.random())
    motor_eye.throttle = random.uniform(-1.0, -0.6)
    time.sleep(random.random())
    motor_eye.throttle = 0
    time.sleep(random.random())



while True:
    if ss.digital_read(attract_switch):  #  regular mode, attrack switch not closed/shorted
        if not ss.digital_read(button):  # button has been pressed
            decoder = audiomp3.MP3Decoder(open("ring.mp3", "rb"))
            audio.play(decoder)
            while audio.playing:
                pass
            open_lid()
            blink(3)
            ss.digital_write(LED, True)  # light the eye
            decoder = audiomp3.MP3Decoder(open(audio_files[current_audio_file], "rb"))
            audio.play(decoder)
            while audio.playing:
                eye_look()
            motor_eye.throttle = 0  # audio is finished, pause the eye
            blink(5)
            close_lid()
            current_audio_file = ((current_audio_file + 1) % (len(audio_files)))  # go to next file

    else:  # attract mode
        open_lid()
        blink(3)
        ss.digital_write(LED, True)
        for _ in range(4):
            eye_look()
        time.sleep(1)
        blink(5)
        close_lid()
        time.sleep(random.randint(2, 8))
