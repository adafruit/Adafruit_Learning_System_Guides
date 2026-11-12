# SPDX-FileCopyrightText: Copyright (c) 2026 Tim Cocks for Adafruit Industries
#
# SPDX-License-Identifier: MIT

"""Viper drawing for code.py: one screen column of waveform per call.

Build ``_audiograph.rv32imc.mpy`` for the Metro ESP32-P4 with build.py (it runs
``mpy-cross -march=rv32imc``) and copy it next to code.py: ``import _audiograph``
loads it.
"""

import micropython
from micropython import const

# ptr8, ptr16 and ptr32 are viper built-ins.
# pylint: disable=undefined-variable, too-many-locals, too-many-branches, too-many-statements
# pylint: disable=chained-comparison

# Palette indices of the waveform bitmap.
BACKGROUND = const(0)
WAVE = const(1)
RMS = const(2)
CLIP = const(3)
GAP = const(4)
# The waveform's colours while not recording, so that what is recorded stands out.
MONITOR_WAVE = const(6)
MONITOR_RMS = const(7)


@micropython.viper
def column(samples, row, config, peaks) -> int:
    """Draw one column of the waveform into ``row`` from interleaved ``samples``.

    ``config`` is array("i") [frames, channels, band, gap, monitor]: each
    channel gets a band of ``band`` pixels (odd, so that zero is a pixel row),
    with ``gap`` pixels between bands. ``row`` holds the palette index of each
    pixel, top first. Like Audacity, the samples' range is drawn in WAVE (CLIP
    when it reaches full scale) and their RMS level, around zero, in RMS.
    When ``monitor`` isn't 0, MONITOR_WAVE and MONITOR_RMS replace WAVE and RMS.
    ``peaks[c]`` is set to channel c's peak absolute value.
    """
    s = ptr16(samples)
    r = ptr8(row)
    c = ptr32(config)
    p = ptr32(peaks)
    frames = c[0]
    channels = c[1]
    band = c[2]
    gap = c[3]
    wave = WAVE
    rms_colour = RMS
    if c[4]:
        wave = MONITOR_WAVE
        rms_colour = MONITOR_RMS
    half = (band - 1) >> 1
    end = frames * channels
    ch = 0
    while ch < channels:
        low = 32767
        high = -32768
        total = 0
        i = ch
        while i < end:
            v = (int(s[i]) << 16) >> 16
            if v < low:
                low = v
            if v > high:
                high = v
            q = v >> 5
            total += q * q
            i += channels
        # Integer square root of the mean square, in units of 32.
        mean = total // frames
        root = mean
        if root > 0:
            guess = (root + 1) >> 1
            while guess < root:
                root = guess
                guess = (root + mean // root) >> 1
        rms = root << 5

        peak = high
        if -low > peak:
            peak = -low
        p[ch] = peak

        base = ch * (band + gap)
        centre = base + half
        top = centre - ((high * half) >> 15)
        bottom = centre - ((low * half) >> 15)
        rms_top = centre - ((rms * half) >> 15)
        rms_bottom = centre + ((rms * half) >> 15)
        colour = wave
        if high >= 32767 or low <= -32767:
            colour = CLIP
        y = base
        stop = base + band
        while y < stop:
            if y < top or y > bottom:
                r[y] = BACKGROUND
            elif colour == wave and y >= rms_top and y <= rms_bottom:
                r[y] = rms_colour
            else:
                r[y] = colour
            y += 1
        if ch < channels - 1:
            while y < stop + gap:
                r[y] = GAP
                y += 1
        ch += 1
    return 0
