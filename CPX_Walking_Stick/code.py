# Talking Cane
# for Adafruit Circuit Playground Express with CircuitPython
from adafruit_circuitplayground.express import cpx

# Change this number to adjust touch sensitivity threshold
cpx.adjust_touch_threshold(600)
# Set the tap type: 1=single, 2=double
cpx.detect_taps = 1

# NeoPixel settings
RED = (90, 0, 0)
BLACK = (0, 0, 0)
step_col = [RED]

cpx.pixels.brightness = 0.1  # set brightness value

# The audio file assigned to the touchpad
audio_file = ["imperial_march.wav"]

def play_it(index):
    cpx.pixels.fill(step_col[index])  # Light neopixels
    cpx.play_file(audio_file[index])  # play audio clip
    print("playing file " + audio_file[index])
    cpx.pixels.fill(BLACK)  # unlight lights

while True:
    # playback mode. Use the slide switch to change between
    #   trigger via touch or via single tap
    if cpx.switch:
        if cpx.touch_A1:
            play_it(0)
    else:
        if cpx.tapped:
            play_it(0)

