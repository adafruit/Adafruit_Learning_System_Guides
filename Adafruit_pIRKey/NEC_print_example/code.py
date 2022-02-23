# SPDX-FileCopyrightText: 2018 Limor Fried for Adafruit Industries
#
# SPDX-License-Identifier: MIT

# Simple NEC remote decode-and-print example
# Prints out the 4-byte code transmitted by NEC remotes

import pulseio
import board
import adafruit_dotstar
import adafruit_irremote

led = adafruit_dotstar.DotStar(board.APA102_SCK, board.APA102_MOSI, 1)
pulsein = pulseio.PulseIn(board.REMOTEIN, maxlen=120, idle_state=True)
decoder = adafruit_irremote.GenericDecode()

# size must match what you are decoding! for NEC use 4
received_code = bytearray(4)

print("Ready for NEC remote input!")

while True:
    led[0] = (0, 0, 0)   # LED off
    pulses = decoder.read_pulses(pulsein)
    print("\tHeard", len(pulses), "Pulses:", pulses)
    try:
        code = decoder.decode_bits(pulses, debug=False)
        led[0] = (0, 100, 0)                         # flash green
        print("Decoded:", code)
    except adafruit_irremote.IRNECRepeatException:   # unusual short code!
        led[0] = (100, 100, 0)                       # flash yellow
        print("NEC repeat!")
    except adafruit_irremote.IRDecodeException as e: # failed to decode
        led[0] = (100, 0, 0)                         # flash red
        print("Failed to decode: ", e.args)

print("----------------------------")
