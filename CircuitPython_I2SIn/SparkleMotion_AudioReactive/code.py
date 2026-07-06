# SPDX-FileCopyrightText: 2026 Tim Cocks for Adafruit Industries
#
# SPDX-License-Identifier: MIT
"""Audio reactive NeoPixels for SparkleMotion.

The louder the sound picked up by the microphone, the more NeoPixels will turn on.

Wiring:
  LED strip   -> board.D19

"""

import array
import math
import time

import board
from audioi2sin import I2SIn
import neopixel

NUM_PIXELS = 30

# uncomment the line matching your device type
PIXEL_PIN = board.D19  # Pin D19 on Sparkle Motion
# PIXEL_PIN = board.D22 # Pin D22 on Sparkle Motion Stick
# PIXEL_PIN = board.D32 # Pin D32 on Mini Sparkle Motion

SAMPLE_RATE = 16000
SAMPLES_PER_FRAME = 512  # ~32 ms windows

pixels = neopixel.NeoPixel(PIXEL_PIN, NUM_PIXELS, brightness=0.3, auto_write=False)

mic = I2SIn(
    bit_clock=board.D26,
    word_select=board.D33,
    data=board.D25,
    sample_rate=SAMPLE_RATE,
    bit_depth=32,
    mono=True,
    left_justified=False,
)

buf = array.array("i", [0] * SAMPLES_PER_FRAME)


def to_signed24(u32):
    return u32 >> 8


def wheel(pos):
    pos = pos % 256
    if pos < 85:
        return (pos * 3, 255 - pos * 3, 0)
    if pos < 170:
        pos -= 85
        return (255 - pos * 3, 0, pos * 3)
    pos -= 170
    return (0, pos * 3, 255 - pos * 3)


# Smoothed noise floor + peak so the effect adapts to the room.
noise_floor = 2000.0
peak = 20000.0
hue = 0
smoothed_level = 0.0

while True:
    mic.record(buf, len(buf))

    # Compute RMS of the window.
    acc = 0
    for raw in buf:
        s = to_signed24(raw)
        acc += s * s
    rms = math.sqrt(acc / len(buf))

    # Track a slow noise floor and a decaying peak for auto-gain.
    noise_floor = 0.995 * noise_floor + 0.005 * rms
    if rms > peak:
        peak = rms
    else:
        peak *= 0.995
    peak = max(peak, noise_floor + 1000)

    level = (rms - noise_floor) / (peak - noise_floor)
    if level < 0:
        level = 0.0
    elif level > 1:
        level = 1.0

    # Smooth the bar so it doesn't jitter on every frame.
    smoothed_level = 0.6 * smoothed_level + 0.4 * level

    lit = int(smoothed_level * NUM_PIXELS)
    hue = (hue + 2) % 256

    for i in range(NUM_PIXELS):
        if i < lit:
            r, g, b = wheel((hue + i * (256 // NUM_PIXELS)) % 256)
            pixels[i] = (r, g, b)
        else:
            pixels[i] = (0, 0, 0)
    pixels.show()

    time.sleep(0.005)
