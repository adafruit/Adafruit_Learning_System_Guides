"""
This example runs the 'Simon' game on the PyRuler.
Memorize each led sequence and tap the corresponding
touch pads on the pyruler to advance to each new sequence.
Code adapted from Miguel Grinberg's Simon game for Circuit Playground Express

"""

import time
import random
import board
from digitalio import DigitalInOut, Direction
import touchio
import adafruit_dotstar

# Initialize dot star led
pixels = adafruit_dotstar.DotStar(board.APA102_SCK, board.APA102_MOSI,
                                  1, brightness=0.1)
red = (255,0,0)
green = (0,255,0)
blue = (0,0,255)

led = DigitalInOut(board.D13)
led.direction = Direction.OUTPUT

touches = [DigitalInOut(board.CAP0)]
for p in (board.CAP1, board.CAP2, board.CAP3):
    touches.append(touchio.TouchIn(p))

leds = []
for p in (board.LED4, board.LED5, board.LED6, board.LED7):
    led = DigitalInOut(p)
    led.direction = Direction.OUTPUT
    leds.append(led)

cap_touches = [False, False, False, False]

def wheel(pos):
    # Input a value 0 to 255 to get a color value.
    # The colours are a transition r - g - b - back to r.
    if pos < 0 or pos > 255:
        return (0, 0, 0)
    if pos < 85:
        return (255 - pos * 3, pos * 3, 0)
    if pos < 170:
        pos -= 85
        return (0, 255 - pos * 3, pos * 3)
    pos -= 170
    return (pos * 3, 0, 255 - pos * 3)

def rainbow_cycle(wait):
    for j in range(255):
        for i in range(len(pixels)):
            rc_index = (i * 256 // len(pixels)) + j
            pixels[i] = wheel(rc_index & 255)
        time.sleep(wait)

def read_caps():
    t0_count = 0
    t0 = touches[0]
    t0.direction = Direction.OUTPUT
    t0.value = True
    t0.direction = Direction.INPUT
    # funky idea but we can 'diy' the one non-hardware captouch device by hand
    # by reading the drooping voltage on a tri-state pin.
    t0_count = t0.value + t0.value + t0.value + t0.value + t0.value + \
               t0.value + t0.value + t0.value + t0.value + t0.value + \
               t0.value + t0.value + t0.value + t0.value + t0.value
    cap_touches[0] = t0_count > 2
    cap_touches[1] = touches[1].raw_value > 3000
    cap_touches[2] = touches[2].raw_value > 3000
    cap_touches[3] = touches[3].raw_value > 3000
    return cap_touches

def timeout_touch(timeout=3):
    start_time = time.monotonic() # start 3 second timer waiting for user input
    while time.monotonic() - start_time < timeout:
        caps = read_caps()
        for i,c in enumerate(caps):
            if c:
                return i

def light_cap(cap, duration=0.5):
    # turn the LED for the selected cap on
    leds[cap].value = True
    time.sleep(duration)
    leds[cap].value = False
    time.sleep(duration)

def play_sequence(seq):
    duration = max(0.1, 1 - len(sequence) * 0.05)
    for cap in seq:
        light_cap(cap, duration)

def read_sequence(seq):
    pixels.fill(green)
    for cap in seq:
        if timeout_touch() != cap:
            # the player made a mistake!
            return False
        light_cap(cap, 0.5)
    return True

while True:
    # led light sequence at beginning of each game
    pixels.fill(blue)
    time.sleep(1)
    for led in leds:
        led.value = True
        time.sleep(0.25)
    for led in leds:
        led.value = False
    sequence = []
    while True:
        pixels.fill(blue) # blue for showing user sequence
        time.sleep(1)
        sequence.append(random.randint(0, 3)) # add new light to sequence each time
        play_sequence(sequence) # show the sequence
        if not read_sequence(sequence): # if user inputs wrong sequence, gameover
            # game over, make dot star red
            pixels.fill(red)
            time.sleep(3)
            print("gameover")
            break
        else:
            print("Next sequence unlocked!")
            rainbow_cycle(0) # Dot star animation after each correct sequence
        pixels.fill(0)
        time.sleep(1)
