# SPDX-FileCopyrightText: 2024 Liz Clark for Adafruit Industries
# SPDX-License-Identifier: MIT

import time
import array
import pulseio
import board
import adafruit_irremote

# Create a 'PulseOut' to send infrared signals on the IR transmitter @ 38KHz
pulseout = pulseio.PulseOut(board.D6, frequency=38000, duty_cycle=2**15)
# Create an encoder that will take numbers and turn them into NEC IR pulses
encoder = adafruit_irremote.GenericTransmit(header=[9000, 4500],
                                            one=[560, 1700],
                                            zero=[560, 560],
                                            trail=0)
# IR receiver setup
ir_receiver = pulseio.PulseIn(board.D5, maxlen=120, idle_state=True)
decoder = adafruit_irremote.GenericDecode()

while True:
    pulses = decoder.read_pulses(ir_receiver)
    try:
        # Attempt to decode the received pulses
        received_code = decoder.decode_bits(pulses)
        if received_code:
            hex_code = ''.join(["%02X" % x for x in received_code])
            print(f"Received: {hex_code}")
            # Convert pulses to an array of type 'H' (unsigned short)
            pulse_array = array.array('H', pulses)
            # send code back using original pulses
            pulseout.send(pulse_array)
            print(f"Sent: {pulse_array}")
    except adafruit_irremote.IRNECRepeatException:  # Signal was repeated, ignore
        pass
    except adafruit_irremote.IRDecodeException:  # Failed to decode signal
        print("Error decoding")
    ir_receiver.clear()  # Clear the receiver buffer
    time.sleep(1)  # Delay to allow the receiver to settle
    print()
