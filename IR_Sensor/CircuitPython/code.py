import board
import pulseio
import adafruit_irremote

IR_PIN = board.D2  # Pin connected to IR receiver.

# Expected pulse, pasted in from previous recording REPL session:
pulse = [9144, 4480, 602, 535, 600, 540, 595, 536, 599, 537, 600, 536,
         596, 540, 595, 544, 591, 539, 596, 1668, 592, 1676, 593, 1667,
         593, 1674, 596, 1670, 590, 1674, 595, 535, 590, 1673, 597, 541,
         595, 536, 597, 538, 597, 538, 597, 1666, 594, 541, 594, 541, 594,
         540, 595, 1668, 596, 1673, 592, 1668, 592, 1672, 601, 540, 592,
         1669, 590, 1672, 598, 1667, 593]

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
pulses = pulseio.PulseIn(IR_PIN, maxlen=200, idle_state=True)
decoder = adafruit_irremote.GenericDecode()
pulses.clear()
pulses.resume()
# Loop waiting to receive pulses.
while True:
    # Wait for a pulse to be detected.
    detected = decoder.read_pulses(pulses)
    print('got a pulse...')
    # Got a pulse, now compare.
    if fuzzy_pulse_compare(pulse, detected):
        print('Received correct remote control press!')
