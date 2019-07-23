import time
import random
from adafruit_circuitplayground.express import cpx

cpx.pixels.brightness = 0.1  # adjust NeoPixel brightness to your liking

REGION_LEDS = (
    (5, 6, 7),  # yellow region
    (2, 3, 4),  # blue region
    (7, 8, 9),  # red region
    (0, 1, 2),  # green region
)

REGION_COLOR = (
    (255, 255, 0),  # yellow region
    (0, 0, 255),    # blue region
    (255, 0, 0),    # red region
    (0, 255, 0),    # green region
)

REGION_TONE = (
    252,  # yellow region
    209,  # blue region
    310,  # red region
    415,  # green region
)

PAD_REGION = {
    'A1': 0,  # yellow region
    'A2': 2,  # red region
    'A3': 2,  # red region
    'A4': 3,  # green region
    'A5': 3,  # green region
    'A6': 1,  # blue region
    'A7': 1,  # blue region
}

def light_region(region, duration=1):
    # turn the LEDs for the selected region on
    for led in REGION_LEDS[region]:
        cpx.pixels[led] = REGION_COLOR[region]

    # play a tone for the selected region
    cpx.start_tone(REGION_TONE[region])

    # wait the requested amount of time
    time.sleep(duration)

    # stop the tone
    cpx.stop_tone()

    # turn the LEDs for the selected region off
    for led in REGION_LEDS[region]:
        cpx.pixels[led] = (0, 0, 0)

def read_region(timeout=30):
    val = 0
    start_time = time.time()
    while time.time() - start_time < timeout:
        if cpx.touch_A1:
            val = PAD_REGION['A1']
        elif cpx.touch_A2:
            val = PAD_REGION['A2']
        elif cpx.touch_A3:
            val = PAD_REGION['A3']
        elif cpx.touch_A4:
            val = PAD_REGION['A4']
        elif cpx.touch_A5:
            val = PAD_REGION['A5']
        elif cpx.touch_A6:
            val = PAD_REGION['A6']
        elif cpx.touch_A7:
            val = PAD_REGION['A7']
    return val

def play_sequence(sequence):
    duration = 1 - len(sequence) * 0.05
    if duration < 0.1:
        duration = 0.1
    for region in sequence:
        light_region(region, duration)

def read_sequence(sequence):
    for region in sequence:
        if read_region() != region:
            # the player made a mistake!
            return False
        light_region(region, 0.25)
    return True

def play_error():
    cpx.start_tone(160)
    time.sleep(1)
    cpx.stop_tone()

def play_game():
    sequence = []
    while True:
        sequence.append(random.randint(0, 3))
        play_sequence(sequence)
        if not read_sequence(sequence):
            # game over
            play_error()
            break
        time.sleep(1)

while True:
    play_game()
