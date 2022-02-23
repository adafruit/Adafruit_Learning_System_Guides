# SPDX-FileCopyrightText: 2018 Limor Fried for Adafruit Industries
#
# SPDX-License-Identifier: MIT

import board
import pulseio
import adafruit_dotstar
import adafruit_irremote

led = adafruit_dotstar.DotStar(board.APA102_SCK, board.APA102_MOSI, 1)
decoder = adafruit_irremote.GenericDecode()
pulsein = pulseio.PulseIn(board.REMOTEIN, maxlen=200, idle_state=True)

# Expected pulse, pasted in from previous recording REPL session:
key1_pulses = [0]  # PUT YOUR PULSECODES HERE!
key2_pulses = [1]  # PUT YOUR PULSECODES HERE!

print('IR listener')
# Fuzzy pulse comparison function:
def fuzzy_pulse_compare(pulse1, pulse2, fuzzyness=0.2):
    if len(pulse1) != len(pulse2):
        return False
    for i in range(len(pulse1)):
        threshold = int(pulse1[i] * fuzzyness)
        if abs(pulse1[i] - pulse2[i]) > threshold:
            return False
    return True

# Create pulse input and IR decoder.
pulsein.clear()
pulsein.resume()

# Loop waiting to receive pulses.
while True:
    led[0] = (0, 0, 0)   # LED off
    # Wait for a pulse to be detected.
    pulses = decoder.read_pulses(pulsein)
    led[0] = (0, 0, 100) # flash blue

    print("\tHeard", len(pulses), "Pulses:", pulses)

    # Got a pulse set, now compare.
    if fuzzy_pulse_compare(key1_pulses, pulses):
        print("****** KEY 1 DETECTED! ******")

    if fuzzy_pulse_compare(key2_pulses, pulses):
        print("****** KEY 2 DETECTED! ******")
