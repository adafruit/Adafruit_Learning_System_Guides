# SPDX-FileCopyrightText: 2026 Anne Barela for Adafruit Industries
# SPDX-FileCopyrightText: 2026 Mikey Sklar for Adafruit Industries
#
# SPDX-License-Identifier: MIT

# An example using the adafruit_moonshine_klatt library to generate speech using an 
#   Adafruit Fruit Jam RP2350 with an onboard TLV320DAC3100 I2S amplifier

# Moonshine Klatt talks at 16 kHz, but the TLV320 library has no 16 kHz setting.
# The code sets two DAC registers by hand below to get there, so pylint is told that is OK.
# pylint: disable=protected-access

import time
import adafruit_tlv320
import audiobusio
import board
import pwmio

import adafruit_moonshine_klatt as speech

VOLUME = 0.85  # 0.0 to 1.0

mclk = pwmio.PWMOut(board.I2S_MCLK, frequency=15_000_000, duty_cycle=2**15)
dac = adafruit_tlv320.TLV320DAC3100(board.I2C())
# The driver has no 16 kHz clock setting. Set up 48 kHz, then raise the DAC oversampling
# (DOSR, page 0 registers 0x0D and 0x0E) from 128 to 384 on the same PLL, giving 16 kHz.
dac.configure_clocks(sample_rate=48000, bit_depth=16, mclk_freq=mclk.frequency)
dac._page0._write_register(0x0D, 384 >> 8)
dac._page0._write_register(0x0E, 384 & 0xFF)
dac.headphone_output = True
dac.speaker_output = True
dac.dac_volume = -63 + VOLUME * 86

audio = audiobusio.I2SOut(board.I2S_BCLK, board.I2S_WS, board.I2S_DIN)

tts = speech.TTS(audio)

while True:
    for voice in tts.voices:
        tts.voice = voice
        start = time.monotonic()
        tts.say(f"Hello from Circuit Python. This is the {voice} voice.")
        print(f"{voice}: {time.monotonic() - start:.2f} s")
        time.sleep(1)
    time.sleep(3)
