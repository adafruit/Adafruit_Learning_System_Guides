"""
'ir_neopixel.py'.

=================================================
control a NeoPixel using an (NEC) IR Remote
requires:
- adafruit_irremote library
- neopixel library
"""
import board
import pulseio
import neopixel
import adafruit_irremote

RED = [True, False, False]
GREEN = [False, True, False]
BLUE = [False, False, True]
YELLOW = [True, True, False]
CYAN = [False, True, True]
MAGENTA = [True, False, True]
WHITE = [True, True, True]
BLACK = [False, False, False]

metro_neopixel = neopixel.NeoPixel(board.NEOPIXEL, 1)

pulsein = pulseio.PulseIn(board.D6, maxlen=120, idle_state=True)
decoder = adafruit_irremote.GenericDecode()
# size must match what you are decoding! for NEC use 4
received_code = bytearray(4)
last_code = None


def set_neopixel_color(color):
    metro_neopixel[0] = color
    metro_neopixel.show()


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
        set_neopixel_color(RED)
    elif code[2] == 119:
        set_neopixel_color(GREEN)
    elif code[2] == 183:
        set_neopixel_color(BLUE)
    elif code[2] == 215:
        set_neopixel_color(YELLOW)
    elif code[2] == 87:
        set_neopixel_color(CYAN)
    elif code[2] == 151:
        set_neopixel_color(MAGENTA)
    elif code[2] == 231:
        set_neopixel_color(WHITE)
    elif code[2] == 215:
        set_neopixel_color(BLACK)
    else:
        set_neopixel_color(BLACK)

    last_code = code
