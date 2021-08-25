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
# Use the third value in mappings above to identify each key in a list
keys = [207, 247, 119, 183, 215, 87, 151, 231, 103, 167, 207, 95,
        79, 175, 239, 111, 223, 159, 143, 255, 191, 127]

last_command = None

while True:
    try:
        pulses = decoder.read_pulses(pulsein)
    except MemoryError as e:
        print("Memory error: ", e)
        continue
    command = None
    try:
        code = decoder.decode_bits(pulses, debug=False)
        if len(code) > 3:
            command = code[2]
        print("Decoded:", command)
    except adafruit_irremote.IRNECRepeatException:  # repeat command
        command = last_command
    except adafruit_irremote.IRDecodeException:  # failed to decode
        pass

    if not command:
        continue
    last_command = command

    key_pressed = keys.index(command)
    if key_pressed <= 9:                  # if the keys 0-9 pressed
        pixels[key_pressed] = (0, 30, 0)  # make the neopixel green
    else:
        pixels.fill((0, 0, 0))  # clear on any non-numeric key
