# SPDX-FileCopyrightText: 2017 John Edgar Park for Adafruit Industries
#
# SPDX-License-Identifier: MIT

# Read Adafruit Remote Codes with Circuit Playground Express
#
# Simplified code based on https://learn.adafruit.com/remote-
# control-tree-ornament-with-circuit-playground-express?view=all
#
import adafruit_irremote
import board
import neopixel
import pulseio

pixels = neopixel.NeoPixel(board.NEOPIXEL, 10)

# Set up the reading of pulses on the IR receiver and the IR library
pulsein = pulseio.PulseIn(board.REMOTEIN, maxlen=120, idle_state=True)
decoder = adafruit_irremote.GenericDecode()

# Example works with the Adafruit mini IR remote #389
# The size below must match what you are decoding! For NEC use 4
received_code = bytearray(4)

# IR Remote Mapping
'''
 1: [255, 2, 247, 8]
 2: [255, 2, 119, 136]
 3: [255, 2, 183, 72]
 4: [255, 2, 215, 40]
 5: [255, 2, 87, 168]
 6: [255, 2, 151, 104]
 7: [255, 2, 231, 24]
 8: [255, 2, 103, 152]
 9: [255, 2, 167, 88]
 0: [255, 2, 207, 48]

^ : [255, 2, 95, 160]
v : [255, 2, 79, 176]
> : [255, 2, 175, 80]
< : [255, 2, 239, 16]

Enter: [255, 2, 111, 144]
Setup: [255, 2, 223, 32]
Stop/Mode: [255, 2, 159, 96]
Back: [255, 2, 143, 112]

Vol - : [255, 2, 255, 0]
Vol + : [255, 2, 191, 64]

Play/Pause: [255, 2, 127, 128]
'''

last_command = None

while True:
    try:
        pulses = decoder.read_pulses(pulsein)
    except MemoryError as e:
        print("Memory error: ", e)
        continue
    print("Heard", len(pulses), "Pulses:", pulses)
    command = None
    try:
        code = decoder.decode_bits(pulses, debug=False)
        if len(code) > 3:
            command = code[2]
        print("Decoded:", code)
    except adafruit_irremote.IRNECRepeatException:  # unusual short code!
        print("NEC repeat!")
        command = last_command
    except adafruit_irremote.IRDecodeException as e:  # failed to decode
        print("Failed to decode:", e)
    except MemoryError as e:
        print("Memory error: ", e)

    if not command:
        continue
    last_command = command

    print("----------------------------")

    if command == 247:  # IR button 1
        pixels[1] = (0, 30, 0)
    elif command == 119:  # 2
        pixels[2] = (0, 30, 0)
    elif command == 183:  # 3
        pixels[3] = (0, 30, 0)
    elif command == 215:  # 4
        pixels[4] = (0, 30, 0)
    elif command == 87:  # 5
        pixels[5] = (0, 30, 0)
    elif command == 151:  # 6
        pixels[6] = (0, 30, 0)
    elif command == 231:  # 7
        pixels[7] = (0, 30, 0)
    elif command == 103:  # 8
        pixels[8] = (0, 30, 0)
    elif command == 167:  # 9
        pixels[9] = (0, 30, 0)
    elif command == 207:
        pixels[0] = (0, 30, 0)
    elif command in (111, 143):
        pixels.fill((0, 0, 0)) # clear on enter or back key
