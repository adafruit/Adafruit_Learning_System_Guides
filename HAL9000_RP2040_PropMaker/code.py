# SPDX-FileCopyrightText: 2023 Phil Burgess for Adafruit Industries
#
# SPDX-License-Identifier: MIT

"""
HAL 9000 demo project for Adafruit Prop Maker Feather RP2040 and "Massive
Arade Button with LED - 100mm red." This simply monitors for button presses
and then randomly plays one WAV file from the CIRCUITPY filesystem.
No soldering required; using quick-connects, LED and button can be wired
to screw terminals on the Prop Maker Feather board.
NOTE: WAV FILES MUST BE 16-BIT. This will be fixed (allowing 8-bit WAVs if
desired) in CircuitPython 9.0.
"""

# pylint: disable=import-error
import os
import random
import time
import audiocore
import audiobusio
import board
import digitalio
import pwmio


# HARDWARE SETUP -----------------------------------------------------------

# LED+ is wired to "Neo" pin on screw terminal header, LED- to GND.
# The LED inside the button is NOT a NeoPixel, just a normal passive LED,
# but that's okay here -- the "Neo" pin can also function like a simple
# 5V digital output or PWM pin.
led = pwmio.PWMOut(board.EXTERNAL_NEOPIXELS)
led.duty_cycle = 65535  # LED ON by default

# Button is wired to GND and "Btn" on screw terminal header:
button = digitalio.DigitalInOut(board.EXTERNAL_BUTTON)
button.direction = digitalio.Direction.INPUT
button.pull = digitalio.Pull.UP

# Enable power to audio amp, etc.
external_power = digitalio.DigitalInOut(board.EXTERNAL_POWER)
external_power.direction = digitalio.Direction.OUTPUT
external_power.value = True

# I2S audio out
audio = audiobusio.I2SOut(board.I2S_BIT_CLOCK, board.I2S_WORD_SELECT, board.I2S_DATA)

# Find all Wave files in CIRCUITPY storage:
wavefiles = [
    file
    for file in os.listdir("/sounds/")
    if (file.endswith(".wav") and not file.startswith("._"))
]
print("Audio files found:", wavefiles)

# FUNCTIONS ----------------------------------------------------------------


def play_file(filename):
    """Plays a WAV file in its entirety (function blocks until done)."""
    print("Playing", filename)
    with open(f"/sounds/{filename}", "rb") as file:
        audio.play(audiocore.WaveFile(file))
        # Randomly flicker the LED a bit while audio plays
        while audio.playing:
            led.duty_cycle = random.randint(5000, 30000)
            time.sleep(0.1)
    led.duty_cycle = 65535  # Back to full brightness


# MAIN LOOP ----------------------------------------------------------------


# Loop simply watches for a button press (button pin pulled to GND, thus
# False) and then plays a random WAV file. Because the WAV-playing function
# will take a few seconds, this doesn't even require button debouncing.
while True:
    if button.value is False:
        play_file(random.choice(wavefiles))
