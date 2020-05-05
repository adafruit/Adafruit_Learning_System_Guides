import time
import board
import displayio
import terminalio
import simpleio
from adafruit_display_text import label
from adafruit_display_shapes.rect import Rect
from adafruit_clue import clue

blink_light = True  # optional flashing backlight on accent
tempo = 120  # in bpm
print("BPM: {}".format(tempo))
time_signature = 4  # Beats per measure
BEEP_DURATION = 0.05
delay = 60 / tempo

clue.display.brightness = 1.0
clue.pixel.brightness = 0.2
screen = displayio.Group(max_size=11)
TEAL = 0x009E98
LT_TEAL = 0x000F0F
GRAY = 0x02403E
BLACK = 0x000000
WHITE = 0xFFFFFF
YELLOW = 0xFFFF00

clue.pixel.fill(0)  # Turn off the pixel

# Setup screen
# BG
color_bitmap = displayio.Bitmap(240, 240, 1)
color_palette = displayio.Palette(1)
color_palette[0] = TEAL
bg_sprite = displayio.TileGrid(color_bitmap, x=0, y=0, pixel_shader=color_palette)
screen.append(bg_sprite)

# title box
title_box = Rect(0, 0, 240, 60, fill=GRAY, outline=None)
screen.append(title_box)

# title text
title_label = label.Label(
    terminalio.FONT, text="Metronome", scale=4, color=TEAL, max_glyphs=11
)
title_label.x = 14
title_label.y = 26
screen.append(title_label)

# interval text
interval_label = label.Label(
    terminalio.FONT, text=("{} BPM".format(tempo)), scale=5, color=WHITE, max_glyphs=7
)
interval_label.x = 20
interval_label.y = 95
screen.append(interval_label)

# mid line
mid_line = Rect(0, 134, 240, 3, fill=GRAY, outline=None)
screen.append(mid_line)

# vert line
vert_line = Rect(117, 134, 3, 56, fill=GRAY, outline=None)
screen.append(vert_line)

# Signature text
sig_label = label.Label(
    terminalio.FONT,
    text=("{}/4".format(time_signature)),
    scale=3,
    color=BLACK,
    max_glyphs=3,
)
sig_label.x = 30
sig_label.y = 160
screen.append(sig_label)

# play text
play_label = label.Label(
    terminalio.FONT, text=(" play"), scale=3, color=BLACK, max_glyphs=5
)
play_label.x = 138
play_label.y = 160
screen.append(play_label)

# footer line
footer_line = Rect(0, 190, 240, 3, fill=GRAY, outline=None)
screen.append(footer_line)

# increment label
increment_label = label.Label(
    terminalio.FONT, text=("-1  +1"), scale=3, color=GRAY, max_glyphs=8
)
increment_label.x = 3
increment_label.y = 220
screen.append(increment_label)

# show the screen
clue.display.show(screen)


def metronome(accent):  # Play metronome sound and flash display
    clue.display.brightness = 0.5  # Dim the display slightly
    if accent == 1:  # Put emphasis on downbeat
        if blink_light:
            clue.pixel.fill(YELLOW)  # Flash the pixel
        simpleio.tone(board.SPEAKER, 1800, BEEP_DURATION)
    else:  # All the other beats in the measure
        if blink_light:
            clue.pixel.fill(LT_TEAL)  # Flash the pixel
        simpleio.tone(board.SPEAKER, 1200, BEEP_DURATION)
    if blink_light:
        clue.pixel.fill(0)  # Turn off the pixel
    clue.display.brightness = 1.0  # Restore display to normal brightness


time.sleep(0.2)
tempo_increment = 1  # increment for tempo value setting
feedback_mode = 0  # 0 is sound and visual, 1 is sound only, 2 is visual only
running = False

t0 = time.monotonic()  # set start time

while True:

    # play/pause
    if clue.button_b:
        if play_label.text == " play":
            play_label.text = "pause"
        else:
            play_label.text = " play"
        running = not running
        time.sleep(0.4)
        beat = 1  # start with downbeat

    # Time Signature change
    if clue.button_a:
        print("sig change")
        if time_signature == 4:
            time_signature = 3
        else:
            time_signature = 4
        sig_label.text = "{}/4".format(time_signature)
        time.sleep(0.4)
        beat = 1  # start with downbeat

    if running and (time.monotonic() - t0) >= delay:
        t0 = time.monotonic()  # reset time before click to maintain accuracy
        metronome(beat)
        beat = beat - 1
        if beat == 0:  # if the downbeat was just played, start at top of measure
            beat = time_signature

    # tempo changes
    if clue.touch_0:
        if tempo_increment is 1:
            tempo_increment = 10
            increment_label.text = "-10 +10"
        else:
            tempo_increment = 1
            increment_label.text = "-1  +1"
        time.sleep(0.2)  # debounce

    if clue.touch_1:
        if tempo > 40:
            tempo = tempo - tempo_increment
            delay = 60 / tempo
            interval_label.text = "{} BPM".format(tempo)
            time.sleep(0.2)  # debounce

    if clue.touch_2:
        if tempo < 330:
            tempo = tempo + tempo_increment
            delay = 60 / tempo
            interval_label.text = "{} BPM".format(tempo)
            time.sleep(0.2)  # debounce
