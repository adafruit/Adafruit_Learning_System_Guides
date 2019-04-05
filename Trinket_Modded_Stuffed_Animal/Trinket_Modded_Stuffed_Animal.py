import time
import analogio
import board
import simpleio
from digitalio import DigitalInOut, Direction

# setup photocell
photocell = analogio.AnalogIn(board.A1) # analog #1 same pin as Digital #2
darkness_min = (2 ** 16) * .05          # light level < 5% means darkness

# setup speaker
speaker = DigitalInOut(board.D1)
speaker.direction = Direction.OUTPUT

# setup servo
servo = simpleio.Servo(board.D0)        # servo motor
angle = 0

def chirp():
    for i in range(200,180,-1):
        play_tone(i,9)

def play_tone(tone_value, duration):
    microseconds = 10 ** 6              # duration divider, convert to microseconds

    for i in range(0, duration):
        i += tone_value * 2
        speaker.value = True
        time.sleep(tone_value / microseconds)
        speaker.value = False
        time.sleep(tone_value / microseconds)

# loop forever...
while True:

    # when photocell goes dark (less than 5%)
    # turn on audio
    # rotate stepper
    if photocell.value < darkness_min:
        chirp()                         # bird chirp noise
        if servo.angle == 0:
            servo.angle = 180           # rotate bird head 180 degrees
        else:
            servo.angle = 0
        time.sleep(.5)                  # leave some time to complete rotation
