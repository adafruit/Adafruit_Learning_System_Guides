# SPDX-FileCopyrightText: 2026 Tim Cocks for Adafruit Industries
#
# SPDX-License-Identifier: MIT
import usb_audio

usb_audio.enable(
    sample_rate=16000, channel_count=1, bits_per_sample=16, microphone=True
)
