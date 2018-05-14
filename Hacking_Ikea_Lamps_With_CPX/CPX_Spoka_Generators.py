import time

from adafruit_circuitplayground.express import cpx


# pylint: disable=stop-iteration-return


def wheel(pos):
    # Input a value 0 to 255 to get a color value.
    # The colours are a transition r - g - b - back to r.
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
    while True:
        for elem in seq:
            yield elem


def rainbow_lamp(seq):
    g = cycle_sequence(seq)
    while True:
        cpx.pixels.fill(wheel(next(g)))
        yield


color_sequences = cycle_sequence([
    range(256),  # rainbow_cycle
    [0],  # red
    [10],  # orange
    [30],  # yellow
    [85],  # green
    [137],  # cyan
    [170],  # blue
    [213],  # purple
    [0, 10, 30, 85, 137, 170, 213],  # party mode
])

heart_rates = cycle_sequence([0, 0.5, 1.0])

heart_rate = 0
last_heart_beat = time.monotonic()
next_heart_beat = last_heart_beat + heart_rate

rainbow = None

cpx.detect_taps = 2
cpx.pixels.brightness = 0.2

while True:
    now = time.monotonic()

    if cpx.tapped or rainbow is None:
        rainbow = rainbow_lamp(next(color_sequences))

    if cpx.shake(shake_threshold=20):
        heart_rate = next(heart_rates)
        last_heart_beat = now
        next_heart_beat = last_heart_beat + heart_rate

    if now >= next_heart_beat:
        next(rainbow)
        last_heart_beat = now
        next_heart_beat = last_heart_beat + heart_rate
