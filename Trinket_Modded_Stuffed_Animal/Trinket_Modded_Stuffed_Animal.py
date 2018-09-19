import time
import analogio
import board
import pulseio
from digitalio import DigitalInOut, Direction

# initialize input/output pins
servo_pin = board.D0            # servo motor

# setup speaker 
speaker_pin = DigitalInOut(board.D1)
speaker_pin.direction = Direction.OUTPUT

# setup photocell
photocell_pin = board.A1        # cds photocell D2 == A1
darkness_min = (2 ** 16) * .05  # light level < 5% means darkness
photocell = analogio.AnalogIn(photocell_pin)

def chirp():
    for i in range(200,180,-1):
        play_tone(i,9)

def play_tone(tone_value, duration):
    microseconds = 10 ** 6      # duration divider to work in microseconds

    for i in range(0, duration):
        i += tone_value * 2
        speaker_pin.value = True 
        time.sleep(tone_value / microseconds)
        speaker_pin.value = False
        time.sleep(tone_value / microseconds)

# loop forever...
while True:

    # turn lights and audio on when dark
    # (less than 50% light on analog pin)
    if photocell.value < darkness_min:
        chirp()                 # bird chirp noise
