# SPDX-FileCopyrightText: 2024 Jeff Epler for Adafruit Industries
#
# SPDX-License-Identifier: MIT

# Stream MP3 audio to I2S decoder
#
# Tested with:
#
#  * Adafruit Metro ESP32-S3
#  * Adafruit Metro ESP32-S2
#  * Adafruit Feather ESP32 V2

import time

import adafruit_connection_manager
import adafruit_requests
import audiobusio
import audiomp3
import board
import wifi

mp3_buffer = bytearray(16384)
mp3_decoder = audiomp3.MP3Decoder("/silence.mp3", mp3_buffer)

pool = adafruit_connection_manager.get_radio_socketpool(wifi.radio)
ssl_context = adafruit_connection_manager.get_radio_ssl_context(wifi.radio)
requests = adafruit_requests.Session(pool, ssl_context)

STREAMING_URL = "https://ice2.somafm.com/dronezone-128-mp3"

if "D27" in dir(board):
    # Feather ESP32 V2 has D27 instead of D11
    i2s = audiobusio.I2SOut(bit_clock=board.D12, word_select=board.D13, data=board.D27)
else:
    i2s = audiobusio.I2SOut(bit_clock=board.D12, word_select=board.D13, data=board.D11)

with requests.get(STREAMING_URL, headers={"connection": "close"}, stream=True) as response:
    mp3_decoder.file = response.socket
    i2s.play(mp3_decoder)
    while i2s.playing:
        time.sleep(0.1)
