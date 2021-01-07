# Simple NEC remote decode-and-type keyboard example
# When used with the Adafruit NEC remote will act like a keyboard and
# type out keypresses.

import time
import pulseio
import board
import adafruit_irremote
from adafruit_hid.keyboard import Keyboard
from adafruit_hid.keycode import Keycode
from adafruit_hid.keyboard_layout_us import KeyboardLayoutUS
import adafruit_dotstar
import usb_hid

led = adafruit_dotstar.DotStar(board.APA102_SCK, board.APA102_MOSI, 1)

# The keyboard object!
time.sleep(1)  # Sleep for a bit to avoid a race condition on some systems
keyboard = Keyboard(usb_hid.devices)
keyboard_layout = KeyboardLayoutUS(keyboard)  # We're in the US :)

# our infrared pulse decoder helpers
pulsein = pulseio.PulseIn(board.REMOTEIN, maxlen=120, idle_state=True)
decoder = adafruit_irremote.GenericDecode()
# size must match what you are decoding! for NEC use 4
received_code = bytearray(4)


# Make a list of lists with the IR code expected and our keypress out's
infrared_to_key = (
    ([255, 2, 191, 64], (Keycode.LEFT_CONTROL, Keycode.UP_ARROW)),  # Vol+
    ([255, 2, 255, 0],  (Keycode.LEFT_CONTROL, Keycode.DOWN_ARROW)), # Vol-
    ([255, 2, 127, 128],(Keycode.SPACE,)),
    ([255, 2, 111, 144],(Keycode.ENTER,)),        # Enter / Save
    ([255, 2, 143, 112],(Keycode.DELETE,)),       # Backwards arrow
    ([255, 2, 159, 96], (Keycode.ESCAPE,)),       # Setup
    ([255, 2, 79, 176], (Keycode.DOWN_ARROW,)),
    ([255, 2, 239, 16], (Keycode.LEFT_ARROW,)),
    ([255, 2, 95, 160], (Keycode.UP_ARROW,)),
    ([255, 2, 175, 80], (Keycode.RIGHT_ARROW,)),
    ([255, 2, 207, 48], (Keycode.ZERO,)),
    ([255, 2, 247, 8],  (Keycode.ONE,)),
    ([255, 2, 119, 136],(Keycode.TWO,)),
    ([255, 2, 183, 72], (Keycode.THREE,)),
    ([255, 2, 215, 40], (Keycode.FOUR,)),
    ([255, 2, 87, 168], (Keycode.FIVE,)),
    ([255, 2, 151, 104],(Keycode.SIX,)),
    ([255, 2, 231, 24], (Keycode.SEVEN,)),
    ([255, 2, 103, 152],(Keycode.EIGHT,)),
    ([255, 2, 167, 88], (Keycode.NINE,)),

)

print("Ready for NEC remote input!")

while True:
    led[0] = (0, 0, 0)   # LED off
    pulses = decoder.read_pulses(pulsein)
    #print("\tHeard", len(pulses), "Pulses:", pulses)
    try:
        code = decoder.decode_bits(pulses, debug=False)
        print("Decoded:", code)
        # Reads 4-byte code transmitted by NEC remotes and
        # sends a matching key command
        for pairs in infrared_to_key:
            if pairs[0] == code:
                led[0] = (0, 100, 0)                   # flash green
                print("Matched IR code to keypresses: ", pairs[1])
                keyboard.press(*pairs[1])
                keyboard.release_all()
    except adafruit_irremote.IRNECRepeatException:     # unusual short code!
        print("NEC repeat!")
    except adafruit_irremote.IRDecodeException as e:   # failed to decode
        led[0] = (100, 0, 0)                           # flash red
        print("Failed to decode: ", e.args)
    print("----------------------------")
