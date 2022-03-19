# SPDX-FileCopyrightText: 2022 John Park for Adafruit Industries
# SPDX-License-Identifier: MIT

# Breakbeat Breadboard based on:
# @todbot / Tod Kurt - https://github.com/todbot/plinkykeeb
# Convert files to appropriate WAV format (mono, 22050 Hz, 16-bit signed) with command:
#  sox loop.mp3 -b 16 -c 1 -r 22050 loop.wav
# put samples in "/wav" folder

import time
import board
import keypad
import audiocore
import audiomixer
from audiopwmio import PWMAudioOut as AudioOut

# wait a little bit so USB can stabilize and not glitch audio
time.sleep(3)

# list of (samples to play, mixer gain level)
wav_files = (
    ('wav/amen_22k16b_160bpm.wav', 1.0),
    ('wav/dnb21580_22k16b_160bpm.wav', 0.9),
    ('wav/drumloopA_22k16b_160bpm.wav', 1.0),
    ('wav/femvoc_330662_22k16b_160bpm.wav', 0.8),
    ('wav/scratch3667_4bar_22k16b_160bpm.wav', 0.5),
    ('wav/pt_limor_modem_vox_01.wav', 0.4),
    ('wav/snowpeaks_22k_s16.wav', 0.8),
    ('wav/dnb21580_22k16b_160bpm_rev.wav', 1.0)
)

# pins used by keyboard
KEY_PINS = (
            board.RX, board.D2, board.D3, board.D4,
            board.D5, board.D6, board.D7, board.D8
)

km = keypad.Keys( KEY_PINS, value_when_pressed=False, pull=True)

audio = AudioOut( board.D10 )  # RP2040 PWM, use RC filter on breadboard
mixer = audiomixer.Mixer(voice_count=len(wav_files), sample_rate=22050, channel_count=1,
                         bits_per_sample=16, samples_signed=True)
audio.play(mixer) # attach mixer to audio playback

for i in range(len(wav_files)):  # start all samples at once for use w handle_mixer
    wave = audiocore.WaveFile(open(wav_files[i][0],"rb"))
    mixer.voice[i].play(wave, loop=True)
    mixer.voice[i].level = 0

def handle_mixer(num, pressed):
    voice = mixer.voice[num]   # get mixer voice
    if pressed:
        voice.level = wav_files[num][1]  # play at level in wav_file list
    else: # released
        voice.level = 0  # mute it


while True:
    event = km.events.get()
    if event:
        if event.key_number < len(wav_files):
            if event.pressed:
                handle_mixer(event.key_number, True)

            if event.released:
                handle_mixer( event.key_number, False )
