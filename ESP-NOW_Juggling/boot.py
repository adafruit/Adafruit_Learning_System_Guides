# SPDX-FileCopyrightText: 2025 John Park for Adafruit Industries
#
# SPDX-License-Identifier: MIT
"""
ESP-NOW MIDI Juggling Bridge
boot.py - Minimal configuration for USB MIDI only
"""

import usb_hid
import usb_midi

# Disable everything except MIDI
usb_hid.disable()  # No HID devices
usb_midi.enable()  # Only MIDI

print("Minimal USB MIDI configuration loaded")
