"""Interactive light show using built-in LED and capacitive touch"""
import time
from rainbowio import colorwheel
import adafruit_dotstar
import board
import touchio

led = adafruit_dotstar.DotStar(board.APA102_SCK, board.APA102_MOSI, 1)
touch_A0 = touchio.TouchIn(board.A0)
touch_A1 = touchio.TouchIn(board.A1)
touch_A2 = touchio.TouchIn(board.A2)


def cycle_sequence(seq):
    """Allows other generators to iterate infinitely"""
    while True:
        for elem in seq:
            yield elem


def rainbow_cycle(seq):
    """Rainbow cycle generator"""
    rainbow_sequence = cycle_sequence(seq)
    while True:
        # pylint: disable=stop-iteration-return
        led[0] = (colorwheel(next(rainbow_sequence)))
        yield


def brightness_cycle():
    """Allows cycling through brightness levels"""
    brightness_value = cycle_sequence([1, 0.8, 0.6, 0.4, 0.2])
    while True:
        # pylint: disable=stop-iteration-return
        led.brightness = next(brightness_value)
        yield


color_sequences = cycle_sequence(
    [
        range(256),  # rainbow_cycle
        [50, 160],  # Python colors!
        [0],  # red
        [85],  # green
        [170],  # blue
    ]
)

cycle_speeds = cycle_sequence([0.1, 0.3, 0.5])

brightness = brightness_cycle()

CYCLE_SPEED_INITIAL = 0.3
cycle_speed_start = time.monotonic()
cycle_speed = cycle_speed_start + CYCLE_SPEED_INITIAL

rainbow = None
touch_A0_state = None
touch_A1_state = None
touch_A2_state = None

while True:
    now = time.monotonic()

    if not touch_A0.value and touch_A0_state is None:
        touch_A0_state = "ready"
    if touch_A0.value and touch_A0_state == "ready" or rainbow is None:
        rainbow = rainbow_cycle(next(color_sequences))
        touch_A0_state = None

    if now >= cycle_speed:
        next(rainbow)
        cycle_speed_start = now
        cycle_speed = cycle_speed_start + CYCLE_SPEED_INITIAL

    if not touch_A1.value and touch_A1_state is None:
        touch_A1_state = "ready"
    if touch_A1.value and touch_A1_state == "ready":
        CYCLE_SPEED_INITIAL = next(cycle_speeds)
        cycle_speed_start = now
        cycle_speed = cycle_speed_start + CYCLE_SPEED_INITIAL
        touch_A1_state = None

    if not touch_A2.value and touch_A2_state is None:
        touch_A2_state = "ready"
    if touch_A2.value and touch_A2_state == "ready":
        next(brightness)
        touch_A2_state = None
