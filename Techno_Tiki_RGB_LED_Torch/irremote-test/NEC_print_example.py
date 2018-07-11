# Simple NEC remote decode-and-print example
# Prints out the 4-byte code transmitted by NEC remotes

import pulseio
import board
import adafruit_irremote

pulsein = pulseio.PulseIn(board.D2, maxlen=120, idle_state=True)
decoder = adafruit_irremote.GenericDecode()

# size must match what you are decoding! for NEC use 4
received_code = bytearray(4)

print("Ready for NEC remote input!")

while True:
    pulses = decoder.read_pulses(pulsein)
    print("\tHeard", len(pulses), "Pulses:", pulses)
    try:
        code = decoder.decode_bits(pulses, debug=False)
        print("Decoded:", code)
    except adafruit_irremote.IRNECRepeatException:   # unusual short code!
        print("NEC repeat!")
    except adafruit_irremote.IRDecodeException as e: # failed to decode
        print("Failed to decode: ", e.args)

print("----------------------------")
