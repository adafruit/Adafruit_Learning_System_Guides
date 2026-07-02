# SPDX-FileCopyrightText: 2026 Tim Cocks for Adafruit Industries
#
# SPDX-License-Identifier: MIT
"""Basic wave file recording example for Metro RP2350 w/ PSRAM.

Records 10 seconds of audio to RAM then writes it to a .wav
file on the sd card.

Must use Metro RP2350 with PSRAM for 10 second recording.

Wiring:
  bclk          -> board.D5
  word select   -> board.D6
  data          -> board.D9

"""
import array
import struct
import time

import board
import audioi2sin


input("press enter to start recording")

#  Recording config
SAMPLE_RATE = 16000
RECORD_SECONDS = 10
CHUNK_SAMPLES = 1024  # samples captured per record() call
OUTPUT_PATH = "/sd/recording.wav"

# Mount SD: Uncomment for devices without builtin SDCard auto-mounting.

# spi = busio.SPI(board.SD_SCK, board.SD_MOSI, board.SD_MISO)
# sdcard = sdcardio.SDCard(spi, cs=board.SD_CARD_DETECT, baudrate=24_000_000)
# vfs = storage.VfsFat(sdcard)
# storage.mount(vfs, "/sd")

#  Mic
# 24-bit MEMS mics ride in 32-bit slots. Downconvert each slot to a
# signed 16-bit PCM sample before writing.
mic = audioi2sin.I2SIn(
    bit_clock=board.D5,
    word_select=board.D6,
    data=board.D9,
    sample_rate=SAMPLE_RATE,
    bit_depth=32,
    mono=True,
    left_justified=False,  # True for SPH0645LM4H
)

actual_rate = mic.sample_rate
print("Recording at", actual_rate, "Hz for", RECORD_SECONDS, "s ->", OUTPUT_PATH)

total_samples = actual_rate * RECORD_SECONDS

# Per-call scratch buffer for the raw 32-bit slots.
raw = array.array("i", [0] * CHUNK_SAMPLES)

# Whole recording buffered in RAM as signed int16 PCM. At 16 kHz mono this is
# ~2 bytes/sample (e.g. 2 s -> 64 KB). Increase RAM headroom or RECORD_SECONDS
# only as far as available memory allows.
pcm16 = array.array("h", [0] * total_samples)


def write_wav_header(file, sample_rate, num_samples, bits_per_sample=16, channels=1):
    byte_rate = sample_rate * channels * bits_per_sample // 8
    block_align = channels * bits_per_sample // 8
    data_size = num_samples * block_align
    file.write(b"RIFF")
    file.write(struct.pack("<I", 36 + data_size))
    file.write(b"WAVE")
    file.write(b"fmt ")
    file.write(
        struct.pack(
            "<IHHIIHH",
            16,  # fmt chunk size
            1,  # PCM
            channels,
            sample_rate,
            byte_rate,
            block_align,
            bits_per_sample,
        )
    )
    file.write(b"data")
    file.write(struct.pack("<I", data_size))


written = 0
start = time.monotonic()

while written < total_samples:
    # Don't overrun the RAM buffer on the final partial chunk.
    request = min(CHUNK_SAMPLES, total_samples - written)
    n = mic.record(raw, request)
    # Convert 24-bit-in-32-bit slots to signed int16. Top 16 bits of each
    # slot are the high bits of the signed 24-bit sample, which is already
    # a serviceable 16-bit PCM representation.
    for i in range(n):
        pcm16[written + i] = raw[i] >> 16
    written += n

elapsed = time.monotonic() - start
print("Captured", written, "samples in", round(elapsed, 2), "s; writing to SD...")
#  Flush the whole capture to SD at once -
with open(OUTPUT_PATH, "wb") as f:
    write_wav_header(f, actual_rate, written)
    f.write(memoryview(pcm16)[:written])

print("Done. Wrote", written, "samples ->", OUTPUT_PATH)

while True:
    pass
