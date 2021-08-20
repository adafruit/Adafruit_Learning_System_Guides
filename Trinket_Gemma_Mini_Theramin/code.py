"""
Adafruit Trinket/Gemma Example: Simple Theramin
Read the voltage from a Cadmium Sulfide (CdS) photocell voltage
divider and output a corresponding tone to a piezo buzzer

Photocell voltage divider center wire to GPIO #2 (analog 1)
and output tone to GPIO #0 (digital 0)
"""

import time

import analogio
import board
import pwmio

photocell_pin = board.A1  # CdS photocell connected to this ANALOG pin
speaker_pin = board.D0  # Speaker is connected to this DIGITAL pin
scale = 0.03  # Change this to adjust tone scale

# Initialize input/output pins
photocell = analogio.AnalogIn(photocell_pin)
pwm = pwmio.PWMOut(speaker_pin, variable_frequency=True, duty_cycle=0)

while True:  # Loop forever...
    # Read photocell analog pin and convert voltage to frequency
    pwm.frequency = 220 + int(scale * float(photocell.value))
    pwm.duty_cycle = 32767  # 50% duty cycle
    time.sleep(0.4)  # Play for 400 ms (adjust to your liking)
    pwm.duty_cycle = 0  # Stop playing
    time.sleep(0.05)  # Delay 50 ms between notes (also adjustable)
