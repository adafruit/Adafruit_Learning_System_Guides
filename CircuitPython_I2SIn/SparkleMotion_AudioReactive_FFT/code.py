# SPDX-FileCopyrightText: 2026 Tim Cocks for Adafruit Industries
#
# SPDX-License-Identifier: MIT
"""Frequency-reactive NeoPixels driven by I2SIn + ulab FFT for SparkleMotion.

Splits each audio window into bass / mid / treble bands and lights a
separate NeoPixel strip for each band, so a kick drum, a snare/voice, and
a hi-hat / cymbal each trigger their own strip.
Wiring:
  bass strip   -> board.D19
  mid strip    -> board.D22
  treble strip -> board.D21
"""
#


import array
import time

import board
from audioi2sin import I2SIn
import neopixel
from ulab import numpy as np

# ---- Audio config ----------------------------------------------------------
SAMPLE_RATE = 16000
# FFT length must be a power of two for ulab. 512 samples = 32 ms windows
# and gives ~31 Hz bin resolution at 16 kHz.
FFT_SIZE = 512

# ---- Strips ----------------------------------------------------------------
STRIPS = (
    # (pin, num_pixels, base_color)
    (board.D19, 30, (255, 30, 0)),  # bass    - warm red/orange
    (board.D22, 8, (0, 255, 80)),  # mid     - green
    (board.D21, 8, (0, 80, 255)),  # treble  - blue
)

# Frequency band edges (Hz) -> indices into the FFT magnitude array.
BAND_EDGES_HZ = (
    (60, 250),  # bass
    (250, 2000),  # mid
    (2000, 6000),  # treble
)

bin_hz = SAMPLE_RATE / FFT_SIZE


def hz_to_bin(hz):
    return max(1, min(FFT_SIZE // 2 - 1, int(hz / bin_hz)))


BAND_BINS = tuple((hz_to_bin(lo), hz_to_bin(hi)) for lo, hi in BAND_EDGES_HZ)

# ---- Init hardware ---------------------------------------------------------
pixel_strips = [
    neopixel.NeoPixel(pin, n, brightness=0.1, auto_write=False) for pin, n, _ in STRIPS
]

mic = I2SIn(
    bit_clock=board.D26,
    word_select=board.D33,
    data=board.D25,
    sample_rate=SAMPLE_RATE,
    bit_depth=32,
    mono=True,
    left_justified=False,  # set True for SPH0645LM4H
)

raw_buf = array.array("i", [0] * FFT_SIZE)

# Per-band auto-gain state.
noise_floor = [1.0] * len(STRIPS)
peak = [10.0] * len(STRIPS)
smoothed = [0.0] * len(STRIPS)


def render_strip(strip, base_color, level):
    n = len(strip)
    lit = int(level * n)
    r0, g0, b0 = base_color
    for i in range(n):
        if i < lit:
            # Brighten the leading pixel, fade the tail.
            f = (i + 1) / max(1, lit)
            strip[i] = (int(r0 * f), int(g0 * f), int(b0 * f))
        else:
            strip[i] = (0, 0, 0)
    strip.show()


while True:
    mic.record(raw_buf, len(raw_buf))

    # This ulab build only has int8/int16 dtypes, no int32. The mic packs
    # a 24-bit signed sample left-justified in each 32-bit slot, so the top
    # 16 bits of every slot are already a signed int16 version of the audio
    # — perfect for FFT band analysis. View the buffer as int16 and take
    # every other halfword (little-endian: high half is at odd indices).
    halfwords = np.frombuffer(raw_buf, dtype=np.int16)
    signed = np.array(halfwords[1::2], dtype=np.float)

    # Remove DC. (Skip a Hann window to save cycles — bands are wide enough
    # that leakage is fine.)
    centered = signed - np.mean(signed)
    re, im = np.fft.fft(centered)
    mags = np.sqrt(re * re + im * im)

    for idx, (lo, hi) in enumerate(BAND_BINS):
        band_energy = float(np.mean(mags[lo:hi]))

        # Slow noise floor, decaying peak, per band.
        noise_floor[idx] = 0.995 * noise_floor[idx] + 0.005 * band_energy
        if band_energy > peak[idx]:
            peak[idx] = band_energy
        else:
            peak[idx] *= 0.99
        if peak[idx] < noise_floor[idx] + 1.0:
            peak[idx] = noise_floor[idx] + 1.0

        _level = (band_energy - noise_floor[idx]) / (peak[idx] - noise_floor[idx])
        if _level < 0:
            _level = 0.0
        elif _level > 1:
            _level = 1.0

        # Bass should feel punchy, treble more responsive.
        attack = 0.6 if idx == 0 else 0.5
        smoothed[idx] = (1 - attack) * smoothed[idx] + attack * _level

        render_strip(pixel_strips[idx], STRIPS[idx][2], smoothed[idx])

    time.sleep(0.002)
