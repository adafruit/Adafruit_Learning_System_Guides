import time
import board
import pulseio
import adafruit_irremote
import neopixel

# Configure treasure information
#                  ID       PIXEL    COLOR
TREASURE_INFO = { (1,)*4 : (  0  , 0xFF0000) ,
                  (2,)*4 : (  1  , 0x00FF00) ,
                  (3,)*4 : (  2  , 0x0000FF) }
treasures_found = dict.fromkeys(TREASURE_INFO.keys(), False)

# Create NeoPixel object to indicate status
pixels = neopixel.NeoPixel(board.NEOPIXEL, 10)

# Sanity check setup
if len(TREASURE_INFO) > pixels.n:
    raise ValueError("More treasures than pixels.")

# Create a 'pulseio' input, to listen to infrared signals on the IR receiver
pulsein = pulseio.PulseIn(board.IR_RX, maxlen=120, idle_state=True)

# Create a decoder that will take pulses and turn them into numbers
decoder = adafruit_irremote.GenericDecode()

while True:
    # Listen for incoming IR pulses
    pulses = decoder.read_pulses(pulsein)

    # Try and decode them
    try:
        # Attempt to convert received pulses into numbers
        received_code = tuple(decoder.decode_bits(pulses))
    except adafruit_irremote.IRNECRepeatException:
        # We got an unusual short code, probably a 'repeat' signal
        # print("NEC repeat!")
        continue
    except adafruit_irremote.IRDecodeException as e:
        # Something got distorted or maybe its not an NEC-type remote?
        # print("Failed to decode: ", e.args)
        continue

    # See if received code matches any of the treasures
    if received_code in TREASURE_INFO.keys():
        treasures_found[received_code] = True
        p, c = TREASURE_INFO[received_code]
        pixels[p] = c

    # Check to see if all treasures have been found
    if False not in treasures_found.values():
        pixels.auto_write = False
        while True:
            # Round and round we go
            pixels.buf = pixels.buf[-3:] + pixels.buf[:-3]
            pixels.show()
            time.sleep(0.1)
