# pylint: disable=multiple-statements,wrong-import-position,wrong-import-order
import gc
from adafruit_hid.keyboard import Keyboard; gc.collect()
from adafruit_hid.keycode import Keycode; gc.collect()
from adafruit_hid.keyboard_layout_us import KeyboardLayoutUS; gc.collect()
import board
import pulseio
import adafruit_dotstar
import adafruit_irremote
import time
import usb_hid

# The keyboard object!
time.sleep(1)  # Sleep for a bit to avoid a race condition on some systems
keyboard = Keyboard(usb_hid.devices)
keyboard_layout = KeyboardLayoutUS(keyboard)  # We're in the US :)

led = adafruit_dotstar.DotStar(board.APA102_SCK, board.APA102_MOSI, 1)
decoder = adafruit_irremote.GenericDecode()
pulsein = pulseio.PulseIn(board.REMOTEIN, maxlen=100, idle_state=True)

# Expected pulse, pasted in from previous recording REPL session:
key1_pulses = [0]

key2_pulses = [1]

print('IR listener')
# Fuzzy pulse comparison function:
def fuzzy_pulse_compare(pulse1, pulse2, fuzzyness=0.2):
    if len(pulse1) != len(pulse2):
        return False
    for i in range(len(pulse1)):
        threshold = int(pulse1[i] * fuzzyness)
        if abs(pulse1[i] - pulse2[i]) > threshold:
            return False
    return True

# Create pulse input and IR decoder.
pulsein.clear()
pulsein.resume()

# Loop waiting to receive pulses.
while True:
    led[0] = (0, 0, 0)   # LED off
    # Wait for a pulse to be detected.
    pulses = decoder.read_pulses(pulsein)
    led[0] = (0, 0, 100) # flash blue

    print("\tHeard", len(pulses), "Pulses:", pulses)
    # Got a pulse set, now compare.
    if fuzzy_pulse_compare(key1_pulses, pulses):
        print("****** KEY 1 DETECTED! ******")
    keyboard.press(Keycode.SPACE)
    keyboard.release_all()

    if fuzzy_pulse_compare(key2_pulses, pulses):
        print("****** KEY 2 DETECTED! ******")
    keyboard_layout.write("hello!")
