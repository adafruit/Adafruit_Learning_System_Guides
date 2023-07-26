# SPDX-FileCopyrightText: 2023 ladyada for Adafruit Industries
#
# SPDX-License-Identifier: MIT

import audiobusio
import audiocore
import board
import digitalio
import keypad
import analogio
import audiomixer

SOUND_FILE = "StreetChicken.wav"

power = digitalio.DigitalInOut(board.EXTERNAL_POWER)
power.switch_to_output(value=True)

analog_pin = analogio.AnalogIn(board.A0)

keys = keypad.Keys((board.BUTTON,), value_when_pressed=False)

i2s = audiobusio.I2SOut(board.I2S_BIT_CLOCK, board.I2S_WORD_SELECT, board.I2S_DATA)
music = audiocore.WaveFile(SOUND_FILE)
mixer = audiomixer.Mixer(voice_count=1, sample_rate=music.sample_rate, channel_count=1,
                         bits_per_sample=music.bits_per_sample, samples_signed=True)
i2s.play(mixer)

sound = False
last_pot = 0

while True:
    if abs(last_pot - analog_pin.value) > 1000:
        last_pot = analog_pin.value
        volume = 1.0 - last_pot / 65535
        print(volume)
        mixer.voice[0].level = volume

    if sound and not mixer.voice[0].playing:
        print("Playing now!")
        mixer.voice[0].play(music)

    event = keys.events.get()
    if event and event.pressed:
        print("click")
        sound = not sound
        mixer.voice[0].stop()
