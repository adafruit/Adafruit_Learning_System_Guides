# SPDX-FileCopyrightText: 2020 Liz Clark for Adafruit Industries
#
# SPDX-License-Identifier: MIT

import time
import board
import audioio
import audiomp3
import framebufferio
import rgbmatrix
import displayio
import adafruit_imageload
import digitalio
from adafruit_display_shapes.rect import Rect
from adafruit_bitmap_font import bitmap_font
from adafruit_display_text import label

#  matrix setup
displayio.release_displays()
matrix = rgbmatrix.RGBMatrix(
    width=64,
    height=32,
    bit_depth=4,
    rgb_pins=[board.D6, board.D5, board.D9, board.D11, board.D10, board.D12],
    addr_pins=[board.A5, board.A4, board.A3, board.A2],
    clock_pin=board.D13,
    latch_pin=board.D0,
    output_enable_pin=board.D1,
)
display = framebufferio.FramebufferDisplay(matrix)

#  display groups
start_group = displayio.Group()
score_group = displayio.Group()

#  text & bg color setup for scoreboard
score_text = "      "
font = bitmap_font.load_font("/Fixedsys-32.bdf")
yellow = (255, 127, 0)
pink = 0xFF00FF

score_text = label.Label(font, text=score_text, color=0x0)
score_text.x = 23
score_text.y = 15

score_bg = Rect(0, 0, 64, 32, fill=yellow, outline=pink, stroke=3)

#  start splash screen graphic
start, start_pal = adafruit_imageload.load("/pixelHoops.bmp",
                                           bitmap=displayio.Bitmap,
                                           palette=displayio.Palette)

start_grid = displayio.TileGrid(start, pixel_shader=start_pal,
                                width=64, height=32)
#  adding graphics to display groups
start_group.append(start_grid)
score_group.append(score_bg)
score_group.append(score_text)

#  start by showing start splash
display.root_group = start_group

#  setup for break beam LED pin
break_beam = digitalio.DigitalInOut(board.A1)
break_beam.direction = digitalio.Direction.INPUT
break_beam.pull = digitalio.Pull.UP

#  setup for button pin
button = digitalio.DigitalInOut(board.D4)
button.direction = digitalio.Direction.INPUT
button.pull = digitalio.Pull.UP

#  setup for speaker pin
speaker = audioio.AudioOut(board.A0)

#  mp3 decoder setup
file = "/hoopBloop0.mp3"
mp3stream = audiomp3.MP3Decoder(open(file, "rb"))

#  state machines used in the loop
score = 0
hoops = False
button_state = False
beam_state = False
sample = 0

while True:
    #  button debouncing
    if not button.value and not button_state:
        button_state = True
    #  debouncing for break beam LED
    if not break_beam.value and not beam_state:
        beam_state = True
    #  if a game hasn't started and you press the button:
    if not button.value and not hoops:
        #  game starts
        hoops = True
        button_state = False
        #  display shows scoreboard
        display.root_group = score_group
        print("start game!")
        time.sleep(0.5)
    if hoops:
        #  if the break beam LED detects a hoop:
        if not break_beam.value and beam_state:
            #  score increase by 2 points
            score += 2
            #  an mp3 plays
            file = "/hoopBloop{}.mp3".format(sample)
            mp3stream.file = open(file, "rb")
            speaker.play(mp3stream)
            print("score!")
            #  resets break beam
            beam_state = False
            #  increases mp3 file count
            #  plays the 3 files in order
            sample = (sample + 1) % 3
        #  score text x pos if 4 digit score
        if score >= 1000:
            score_text.x = -1
        #  score text x pos if 3 digit score
        elif score >= 100:
            score_text.x = 7
        #  score text x pos if 2 digit score
        elif score >= 10:
            score_text.x = 16
        elif score >= 0:
            score_text.x = 23
        #  updates score text to show current score
        score_text.text = score
        time.sleep(0.01)
    #  if a game is in progress and you press the button:
    if not button.value and hoops:
        #  game stops
        hoops = False
        button_state = False
        #  score is reset to 0
        score = 0
        score_text.text = score
        #  display shows the start splash graphic
        display.root_group = start_group
        print("end game!")
        time.sleep(0.5)
