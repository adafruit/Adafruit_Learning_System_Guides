"""
'ir_sensor.py'.

=================================================
control a LED with an IR Remote
requires:
- adafruit_irremote library
"""

import adafruit_irremote
import board
import digitalio
import pulseio

led = digitalio.DigitalInOut(board.D11)
led.switch_to_output()

pulsein = pulseio.PulseIn(board.D6, maxlen=120, idle_state=True)
decoder = adafruit_irremote.GenericDecode()
# size must match what you are decoding! for NEC use 4
received_code = bytearray(4)
last_code = None

while True:
    try:
        pulses = decoder.read_pulses(pulsein)
    except MemoryError as e:
        print("Memory Error Occured: ", e)
        continue

    try:
        code = decoder.decode_bits(pulses, debug=False)
    except adafruit_irremote.IRNECRepeatException:
        print("NEC Code Repeated, doing last command")
        code = last_code
    except adafruit_irremote.IRDecodeException as e:
        print("Failed to decode: ", e)
    except MemoryError as e:
        print("Memory Error Occured: ", e)

    print(code[2])
    if code[2] == 247:
        led.value = True
    else:
        led.value = False

    last_code = code
