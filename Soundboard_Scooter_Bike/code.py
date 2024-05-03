# SPDX-FileCopyrightText: 2022 John Park for Adafruit Industries
# SPDX-License-Identifier: MIT

# Convert files to appropriate WAV format (mono, 22050 Hz, 16-bit signed)

import time
import board
import keypad
import audiocore
import audiomixer
import audiobusio

# wait a little bit so USB can stabilize and not glitch audio
time.sleep(3)

# list of (samples to play, mixer gain level)
wav_files = (
    ('wav/airhorn.wav', 1.0), #Honk sound 1
    ('wav/bike-horn.wav', 1.0), #Honk around 2
    ('wav/chime.wav', 1.0), #Honk sound 3
    ('wav/idle.wav', 1.0) #Looping Engine Sound Effect
)

# pins used by keyboard
KEY_PINS = (
            board.D5, board.D6, board.D12
)

km = keypad.Keys( KEY_PINS, value_when_pressed=False, pull=True)

audio = audiobusio.I2SOut(board.RX, board.TX, board.D9)

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
    mixer.voice[3].level = 1 #Looping Engine Sound Effect
    event = km.events.get()
    if event:
        if event.key_number < len(wav_files):
            if event.pressed:
                handle_mixer(event.key_number, True)

            if event.released:
                handle_mixer( event.key_number, False )
