# FruitBox Sequencer
# for Adafruit Circuit Playground express
# with CircuitPython

from adafruit_circuitplayground.express import cpx
import time

# Change this number to adjust touch sensitivity threshold, 0 is default
cpx.adjust_touch_threshold(600)

bpm = 60  # quarter note beats per minute, change this to suit your tempo

beat = 15 / bpm  # 16th note expressed as seconds

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
audiofiles = ["fB_bd_tek.wav", "fB_elec_hi_snare.wav", "fB_elec_cymbal.wav",
              "fB_elec_blip2.wav", "fB_bd_zome.wav", "fB_bass_hit_c.wav",
              "fB_drum_cowbell.wav"]

stepAdvance = 0  # to count steps
step = 0

# sixteen steps in a sequence
stepNote = [1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 1, 1, 1, 1]

# step pixels
stepPixel = [9, 8, 7, 6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]

# step colors
stepCol = [WHITE, RED, YELLOW, GREEN, AQUA, BLUE, PURPLE, BLACK]

def prog_mode(i):
    cpx.play_file(audiofiles[i])
    stepNote[step] = i
    cpx.pixels[stepPixel[step]] = stepCol[stepNote[step]]
    print("playing file " + audiofiles[i])


while True:
    # playback mode
    if cpx.switch:  # switch is slid to the left, play mode

        cpx.red_led = False

        if cpx.button_a:
            cpx.pixels.fill(GREEN)
            time.sleep(.2)
            cpx.pixels.fill(BLACK)

        if cpx.button_b:
            for i in range(16):
                step = i
                # light a pixel
                cpx.pixels[stepPixel[i]] = stepCol[stepNote[i]]
                cpx.pixels[stepPixel[i - 1]] = BLACK

                # play a file
                cpx.play_file(audiofiles[stepNote[i]])

                # sleep a beat
                time.sleep(beat)
            cpx.pixels.fill(BLACK)

    # beat programming mode
    else:  # switch is slid to the right, record mode
        cpx.red_led = True
        if cpx.button_a:  # clear pixels, reset step to first step
            cpx.pixels.fill(RED)
            time.sleep(.2)
            cpx.pixels.fill(BLACK)
            cpx.pixels[9] = WHITE
            step = 0
            stepAdvance = 0

        # press B button to advance neo pixel steps
        if cpx.button_b:  # button has been pressed
            stepAdvance += 1
            step = stepAdvance % 16
            cpx.play_file(audiofiles[stepNote[step]])
            cpx.pixels[stepPixel[step]] = stepCol[stepNote[step]]
            cpx.pixels[stepPixel[step - 1]] = BLACK

        if cpx.touch_A1:
            prog_mode(0)
        if cpx.touch_A2:
            prog_mode(1)
        if cpx.touch_A3:
            prog_mode(2)
        if cpx.touch_A4:
            prog_mode(3)
        if cpx.touch_A5:
            prog_mode(4)
        if cpx.touch_A6:
            prog_mode(5)
        if cpx.touch_A7:
            prog_mode(6)
