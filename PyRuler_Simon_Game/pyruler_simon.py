import os
import board
from digitalio import DigitalInOut, Direction
import time
import random
import touchio
import adafruit_dotstar

#pixels = adafruit_dotstar.DotStar(APA102_MOSI, APA102_SCK, 1, brightness=0.1, auto_write=False)
#pixels.fill(0,255,0)
#pixels.show()

led = DigitalInOut(board.D13)
led.direction = Direction.OUTPUT

touches = [DigitalInOut(board.CAP0)]
for p in (board.CAP1, board.CAP2, board.CAP3):
    touches.append(touchio.TouchIn(p))

leds = []
for p in (board.LED4, board.LED5, board.LED6, board.LED7):
    led = DigitalInOut(p)
    led.direction = Direction.OUTPUT
    led.value = True
    time.sleep(0.25)
    leds.append(led)
for led in leds:
    led.value = False

cap_touches = [False, False, False, False]

def read_caps(timeout=30):
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

def record_caps():
    caps = read_caps()
    val = 0
    for i,c in enumerate(caps):
        if c:
            val = i
    return val

def light_cap(cap, duration=0.5):
    # turn the LED for the selected cap on
    leds[cap].value = True
    # wait the requested amount of time
    time.sleep(duration)
    # turn the LED for the selected region off
    leds[cap].value = False
    time.sleep(duration)

def play_sequence(sequence):
    duration = 1 - len(sequence) * 0.05
    if duration < 0.1:
        duration = 0.1
    for cap in sequence:
        light_cap(cap, duration)

def read_sequence(sequence):
    for cap in sequence:
        if record_caps() != cap:
            # the player made a mistake!
            return False
        light_cap(cap, 0.5)
    return True

def play_error():
    # make dot star red
    time.sleep(1)

def play_game():
    sequence = []
    while True:
        time.sleep(1)
        sequence.append(random.randint(0, 3))
        play_sequence(sequence)
        print("Next sequence unlocked!")

        if not read_sequence(sequence):
            # game over
            play_error()
            print("gameover")
            break

        time.sleep(1)

while True:
    play_game()