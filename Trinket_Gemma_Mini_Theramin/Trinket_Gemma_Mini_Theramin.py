# Adafruit Trinket/Gemma Example: Simple Theramin
# Read the voltage from a Cadmium Sulfide (CdS) photocell voltage
# divider and output a corresponding tone to a piezo buzzer
#
# Photocell voltage divider center wire to GPIO #2 (analog 1)
# and output tone to GPIO #0 (digital 0)

import board
import analogio
import digitalio
import time

speaker_pin   = board.D0  # Speaker is connected to this DIGITAL pin
photocell_pin = board.A1  # CdS photocell connected to this ANALOG pin
scale         = 0.03      # Change this to adjust tone scale

readpin  = analogio.AnalogIn(photocell_pin)
writepin = digitalio.DigitalInOut(speaker_pin)
writepin.direction = digitalio.Direction.OUTPUT

while True:  # Loop forever...
	# Read photocell analog pin and convert voltage to frequency
	freq_hz = 220 + readpin.value * scale

	delay_amount = 0.5 / freq_hz     # 1/2 Frequency
	note_start   = time.monotonic()  # Time when note started
	while time.monotonic() - note_start < 0.4:  # For 400 milliseconds...
		writepin.value = True    # Set pin high
		time.sleep(delay_amount) # Wait for 1/2 of note frequency
		writepin.value = False   # Set pin low
		time.sleep(delay_amount) # Wait for other 1/2 of note freq.

	time.sleep(0.05)  # Delay 50 ms between notes (also adjustable)
