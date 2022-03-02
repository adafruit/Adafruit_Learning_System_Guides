# SPDX-FileCopyrightText: 2018 Kattni Rembor for Adafruit Industries
#
# SPDX-License-Identifier: MIT

import pulseio
import board
import adafruit_irremote
from adafruit_circuitplayground.express import cpx

# Create a 'pulseio' input, to listen to infrared signals on the IR receiver
pulsein = pulseio.PulseIn(board.IR_RX, maxlen=120, idle_state=True)
# Create a decoder that will take pulses and turn them into numbers
decoder = adafruit_irremote.GenericDecode()

while True:
    pulses = decoder.read_pulses(pulsein)
    try:
        # Attempt to convert received pulses into numbers
        received_code = decoder.decode_bits(pulses, debug=False)
    except adafruit_irremote.IRNECRepeatException:
        # We got an unusual short code, probably a 'repeat' signal
        # print("NEC repeat!")
        continue
    except adafruit_irremote.IRDecodeException as e:
        # Something got distorted or maybe its not an NEC-type remote?
        # print("Failed to decode: ", e.args)
        continue

    print("NEC Infrared code received: ", received_code)
    if received_code == [255, 2, 255, 0]:
        print("Button A signal")
        cpx.pixels.fill((130, 0, 100))
    if received_code == [255, 2, 191, 64]:
        print("Button B Signal")
        cpx.pixels.fill((0, 0, 0))
        cpx.play_tone(262, 1)
