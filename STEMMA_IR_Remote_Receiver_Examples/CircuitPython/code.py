# SPDX-FileCopyrightText: Copyright (c) 2024 ladyada for Adafruit Industries
#
# SPDX-License-Identifier: MIT

import board
import pulseio
import adafruit_irremote

# IR receiver setup
ir_receiver = pulseio.PulseIn(board.D5, maxlen=120, idle_state=True)
decoder = adafruit_irremote.GenericDecode()

def decode_ir_signals(p):
    codes = decoder.decode_bits(p)
    return codes

while True:
    pulses = decoder.read_pulses(ir_receiver)
    try:
        # Attempt to decode the received pulses
        received_code = decode_ir_signals(pulses)
        if received_code:
            hex_code = ''.join(["%02X" % x for x in received_code])
        print(f"Received: {hex_code}")
    except adafruit_irremote.IRNECRepeatException:  # Signal was repeated, ignore
        pass
    except adafruit_irremote.IRDecodeException:  # Failed to decode signal
        print("Error decoding")
