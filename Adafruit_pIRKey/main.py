# Simple IR remote listener example
# Good for basic testing!

import pulseio
import board
import adafruit_dotstar
import adafruit_irremote

led = adafruit_dotstar.DotStar(board.APA102_SCK, board.APA102_MOSI, 1)
decoder = adafruit_irremote.GenericDecode()
pulsein = pulseio.PulseIn(board.REMOTEIN, maxlen=200, idle_state=True)

while True:
    led[0] = (0, 0, 0)   # LED off
    pulses = decoder.read_pulses(pulsein)
    led[0] = (0, 0, 100) # flash blue
    print("\tHeard", len(pulses), "Pulses:", pulses)
