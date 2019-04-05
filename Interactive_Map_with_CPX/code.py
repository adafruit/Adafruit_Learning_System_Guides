# Interactive Map
# for Adafruit Circuit Playground express
# with CircuitPython

from adafruit_circuitplayground.express import cpx

# Change this number to adjust touch sensitivity threshold, 0 is default
cpx.adjust_touch_threshold(600)

WHITE = (30, 30, 30)
RED = (90, 0, 0)
YELLOW = (45, 45, 0)
GREEN = (0, 90, 0)
AQUA = (0, 45, 45)
BLUE = (0, 0, 90)
PURPLE = (45, 0, 45)
BLACK = (0, 0, 0)

cpx.pixels.brightness = 0.1  # set brightness value

# The seven files assigned to the touchpads
audio_file = ["01.wav", "02.wav", "03.wav",
              "04.wav", "05.wav", "06.wav",
              "07.wav"]

# NeoPixel colors
step_col = [RED, YELLOW, GREEN, AQUA, BLUE, PURPLE, WHITE]

def play_it(index):
    cpx.pixels.fill(step_col[index])  # Light lights
    cpx.play_file(audio_file[index])  # play clip
    print("playing file " + audio_file[index])
    cpx.pixels.fill(BLACK)  # unlight lights

while True:
    # playback mode

    if cpx.touch_A1:
        play_it(0)
    if cpx.touch_A2:
        play_it(1)
    if cpx.touch_A3:
        play_it(2)
    if cpx.touch_A4:
        play_it(3)
    if cpx.touch_A5:
        play_it(4)
    if cpx.touch_A6:
        play_it(5)
    if cpx.touch_A7:
        play_it(6)
