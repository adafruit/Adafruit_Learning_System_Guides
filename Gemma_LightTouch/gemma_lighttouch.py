"""Interactive light show using built-in LED and capacitive touch"""
import time
import adafruit_dotstar
import touchio
import board

LED = adafruit_dotstar.DotStar(board.APA102_SCK, board.APA102_MOSI, 1)
TOUCH_A0 = touchio.TouchIn(board.A0)
TOUCH_A1 = touchio.TouchIn(board.A1)
TOUCH_A2 = touchio.TouchIn(board.A2)


def wheel(pos):
    """ Input a value 0 to 255 to get a color value.
    The colours are a transition r - g - b - back to r."""
    if pos < 0 or pos > 255:
        return 0, 0, 0
    if pos < 85:
        return int(255 - pos * 3), int(pos * 3), 0
    if pos < 170:
        pos -= 85
        return 0, int(255 - pos * 3), int(pos * 3)
    pos -= 170
    return int(pos * 3), 0, int(255 - (pos * 3))


def cycle_sequence(seq):
    """Allows other generators to iterate infinitely"""
    while True:
        for elem in seq:
            yield elem


def rainbow_lamp(seq):
    """Rainbow cycle generator"""
    rainbow = cycle_sequence(seq)
    while True:
        # pylint: disable=stop-iteration-return
        LED[0] = (wheel(next(rainbow)))
        yield


def brightness_lamp():
    """Allows cycling through brightness levels"""
    brightness_value = cycle_sequence([1, 0.8, 0.6, 0.4, 0.2])
    while True:
        # pylint: disable=stop-iteration-return
        LED.brightness = next(brightness_value)
        yield


COLOR_SEQUENCES = cycle_sequence(
    [
        range(256),  # rainbow_cycle
        [50, 160],  # Python colors!
        [0],  # red
        [85],  # green
        [170],  # blue
    ]
)


CYCLE_SPEEDS = cycle_sequence([0.1, 0.3, 0.5])

BRIGHTNESS = brightness_lamp()

CYCLE_SPEED_INITIAL = 0.3
CYCLE_SPEED_START = time.monotonic()
CYCLE_SPEED = CYCLE_SPEED_START + CYCLE_SPEED_INITIAL

RAINBOW = None
TOUCH_A0_STATE = None
TOUCH_A1_STATE = None
TOUCH_A2_STATE = None

while True:
    NOW = time.monotonic()

    if not TOUCH_A0.value and TOUCH_A0_STATE is None:
        TOUCH_A0_STATE = "touched"
    if TOUCH_A0.value and TOUCH_A0_STATE == "touched" or RAINBOW is None:
        RAINBOW = rainbow_lamp(next(COLOR_SEQUENCES))
        TOUCH_A0_STATE = None

    if NOW >= CYCLE_SPEED:
        next(RAINBOW)
        CYCLE_SPEED_START = NOW
        CYCLE_SPEED = CYCLE_SPEED_START + CYCLE_SPEED_INITIAL

    if not TOUCH_A1.value and TOUCH_A1_STATE is None:
        TOUCH_A1_STATE = "touched"
    if TOUCH_A1.value and TOUCH_A1_STATE == "touched":
        CYCLE_SPEED_INITIAL = next(CYCLE_SPEEDS)
        CYCLE_SPEED_START = NOW
        CYCLE_SPEED = CYCLE_SPEED_START + CYCLE_SPEED_INITIAL
        TOUCH_A1_STATE = None

    if not TOUCH_A2.value and TOUCH_A2_STATE is None:
        TOUCH_A2_STATE = "touched"
    if TOUCH_A2.value and TOUCH_A2_STATE == "touched":
        next(BRIGHTNESS)
