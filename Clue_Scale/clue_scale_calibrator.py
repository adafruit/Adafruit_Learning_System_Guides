# SPDX-FileCopyrightText: 2022 Jan Goolsbey for Adafruit Industries
# SPDX-License-Identifier: MIT
#
# clue_scale_calibrator.py
# 2022-07-29 v1.1.0
#
# Clue Scale Calibrator - Single Channel Version
# Adafruit NAU7802 Stemma breakout example

import time
import board
from adafruit_clue import clue
from cedargrove_nau7802 import NAU7802

clue.pixel.brightness = 0.2  # Set NeoPixel brightness
clue.pixel[0] = clue.YELLOW  # Set status indicator to yellow (initializing)

SAMPLE_AVG = 500  # Number of sample values to average
DEFAULT_GAIN = 128  # Default gain for internal PGA

# Instantiate 24-bit load sensor ADC
nau7802 = NAU7802(board.I2C(), address=0x2A, active_channels=1)


def zero_channel():
    """Initiate internal calibration and zero the current channel. Use after
    power-up, a new channel is selected, or to adjust for measurement drift.
    Can be used to zero the scale with a tare weight."""
    nau7802.calibrate("INTERNAL")
    nau7802.calibrate("OFFSET")


def read(samples=100):
    # Read and average consecutive raw sample values; return average raw value
    sample_sum = 0
    sample_count = samples
    while sample_count > 0:
        if nau7802.available:
            sample_sum = sample_sum + nau7802.read()
            sample_count -= 1
    return int(sample_sum / samples)


# Activate the NAU780 internal analog circuitry, set gain, and calibrate/zero
nau7802.enable(True)
nau7802.gain = DEFAULT_GAIN  # Use default gain
zero_channel()  # Calibrate and zero

print("-----------------------------------")
print(" NAU7802 SINGLE CHANNEL CALIBRATOR")
print("-----------------------------------")
print("Place a calibration weight on the")
print("load cell.")
print("To re-zero the load cell, remove")
print("any weights then press and hold A.")
print("-----------------------------------")
print("")

# Play "welcome" tones
clue.play_tone(1660, 0.15)
clue.play_tone(1440, 0.15)

# Main loop: Read sample and display value
while True:
    clue.pixel[0] = clue.GREEN  # Set status indicator to green

    # Read the raw value; print raw value, gain setting, and % of full-scale
    value = read(SAMPLE_AVG)
    print(f"CHAN_{nau7802.channel:1.0f} RAW VALUE: {value:7.0f}")
    print(f"GAIN: x{DEFAULT_GAIN}  full-scale: {(value / ((2**23) - 1)) * 100:3.2f}%")
    print("===================================")

    time.sleep(0.1)

    if clue.button_a:
        # Zero and recalibrate the NAU780
        clue.play_tone(1660, 0.3)  # Play "button pressed" tone
        clue.pixel[0] = clue.RED  # Set status indicator to red (stopped)
        zero_channel()
        while clue.button_a:
            # Wait until button is released
            time.sleep(0.1)
        print("RECALIBRATED")
        clue.play_tone(1440, 0.5)  # Play "reset completed" tone
