# SPDX-FileCopyrightText: 2022 Liz Clark for Adafruit Industries
# SPDX-License-Identifier: MIT
# Based on irremote_transmit.py for CPX by ladyada

import time
import pulseio
import board
import adafruit_irremote

# Create a 'PulseOut' to send infrared signals on the IR transmitter @ 38KHz
pulseout = pulseio.PulseOut(board.D5, frequency=38000, duty_cycle=2**15)
# Create an encoder that will take numbers and turn them into NEC IR pulses
encoder = adafruit_irremote.GenericTransmit(header=[9000, 4500],
                                            one=[560, 1700],
                                            zero=[560, 560],
                                            trail=0)

#  count variable
count = 0

while True:
	#  send IR pulse
    emitter.transmit(pulseout, [255, 2, 255, 0])
	#  increase count
    count += 1
	#  print to REPL
    print("IR signal sent %d times!" % count)
	#  two second delay
    time.sleep(2)
