# SPDX-FileCopyrightText: 2023 John Park and @todbot / Tod Kurt
#
# SPDX-License-Identifier: MIT

import time
import board
import digitalio
import audiomixer
import synthio

# for PWM audio with an RC filter
#import audiopwmio
#audio = audiopwmio.PWMAudioOut(board.GP10)

# for I2S audio with external I2S DAC board
import audiobusio

# I2S on Audio BFF or Amp BFF on QT Py:
# audio = audiobusio.I2SOut(bit_clock=board.A3, word_select=board.A2, data=board.A1)

# I2S audio on PropMaker Feather RP2040
power = digitalio.DigitalInOut(board.EXTERNAL_POWER)
power.switch_to_output(value=True)
audio = audiobusio.I2SOut(board.I2S_BIT_CLOCK, board.I2S_WORD_SELECT, board.I2S_DATA)

mixer = audiomixer.Mixer(channel_count=1, sample_rate=22050, buffer_size=2048)

amp_env_slow = synthio.Envelope(
                                attack_time=0.2,
                                sustain_level=1.0,
                                release_time=0.8
)

amp_env_fast = synthio.Envelope(
                                attack_time=0.1,
                                sustain_level=0.5,
                                release_time=0.2
)


synth = synthio.Synthesizer(channel_count=1, sample_rate=22050, envelope=amp_env_slow)

audio.play(mixer)
mixer.voice[0].play(synth)
mixer.voice[0].level = 0.2

while True:
    synth.envelope = amp_env_slow
    synth.press(46)
    time.sleep(1.25)
    synth.release(46)
    time.sleep(1.25)

    synth.envelope = amp_env_fast
    synth.press(51)
    time.sleep(1.25)
    synth.release(51)
    time.sleep(1.25)
