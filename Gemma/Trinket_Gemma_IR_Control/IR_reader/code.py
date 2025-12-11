# SPDX-FileCopyrightText: 2018 Mikey Sklar for Adafruit Industries
#
# SPDX-License-Identifier: MIT

import time

import adafruit_irremote
import board
import pulseio

IR_PIN = board.D2  # Pin connected to IR receiver.

print('IR listener')
print()
# Create pulse input and IR decoder.
pulses = pulseio.PulseIn(IR_PIN, maxlen=200, idle_state=True)
decoder = adafruit_irremote.GenericDecode()

# Loop waiting to receive pulses.
while True:
    # make sure pulses is empty
    # small delay for cleaner results
    pulses.clear()
    pulses.resume()
    time.sleep(.1)

    # Wait for a pulse to be detected.
    detected = decoder.read_pulses(pulses)

    # print the number of pulses detected
    # note: pulse count is an excellent indicator as to the quality of IR code
    # received.
    #
    # If you are expecting 67 each time (Adafruit Mini Remote Control #389)
    # and only receive 57 this will result in a incomplete listener

    print("pulse count: ", len(detected))

    # print in list form of the pulse duration in microseconds
    # typically starts with ~9,000 microseconds followed by a ~4,000
    # microseconds which is standard IR preamble

    print(detected)
    print()
