# SPDX-FileCopyrightText: 2020 John Park for Adafruit Industries
#
# SPDX-License-Identifier: MIT

"""
Start a 20 second hand washing timer via proximity sensor.
Countdown the seconds with text and beeps.
Display a bitmaps for waiting and washing modes.
"""

import time
import board
from adafruit_clue import clue
from adafruit_display_text import label
from adafruit_bitmap_font import bitmap_font
import displayio
import pwmio

clue.display.brightness = 0.8
clue_display = displayio.Group()

# draw the background image
WASH_ON_FILENAME = "wash_on.bmp"

# CircuitPython 6 & 7 compatible
wash_on_file = open(WASH_ON_FILENAME, "rb")
wash_on_bmp = displayio.OnDiskBitmap(wash_on_file)
wash_on_sprite = displayio.TileGrid(
    wash_on_bmp,
    pixel_shader=getattr(wash_on_bmp, 'pixel_shader', displayio.ColorConverter())
)

# # CircuitPython 7+ compatible
# wash_on_bmp = displayio.OnDiskBitmap(WASH_ON_FILENAME)
# wash_on_sprite = displayio.TileGrid(wash_on_bmp, pixel_shader=wash_on_bmp.pixel_shader)

clue_display.append(wash_on_sprite)

# draw the foreground image
WASH_OFF_FILENAME = "wash_off.bmp"

# CircuitPython 6 & 7 compatible
wash_off_file = open(WASH_OFF_FILENAME, "rb")
wash_off_bmp = displayio.OnDiskBitmap(wash_off_file)
wash_off_sprite = displayio.TileGrid(
    wash_off_bmp,
    pixel_shader=getattr(wash_off_bmp, 'pixel_shader', displayio.ColorConverter())
)

# # CircuitPython 7+ compatible
# wash_off_bmp = displayio.OnDiskBitmap(WASH_OFF_FILENAME)
# wash_off_sprite = displayio.TileGrid(wash_off_bmp, pixel_shader=wash_off_bmp.pixel_shader)

clue_display.append(wash_off_sprite)


# Create text
# first create the group
text_group = displayio.Group()
# Make a label
title_font = bitmap_font.load_font("/font/RacingSansOne-Regular-38.bdf")
title_font.load_glyphs("HandWashTimer".encode('utf-8'))
title_label = label.Label(title_font, text="Hand Wash", color=0x001122)
# Position the label
title_label.x = 10
title_label.y = 16
# Append label to group
text_group.append(title_label)

title2_label = label.Label(title_font, text="Timer", color=0x001122)
# Position the label
title2_label.x = 6
title2_label.y = 52
# Append label to group
text_group.append(title2_label)

timer_font = bitmap_font.load_font("/font/RacingSansOne-Regular-29.bdf")
timer_font.load_glyphs("0123456789ADSWabcdefghijklmnopqrstuvwxyz:!".encode('utf-8'))
timer_label = label.Label(timer_font, text="Wave to start", color=0x4f3ab1)
timer_label.x = 24
timer_label.y = 100
text_group.append(timer_label)

clue_display.append(text_group)
clue.display.root_group = clue_display

def countdown(seconds):
    for i in range(seconds):
        buzzer.duty_cycle = 2**15
        timer_label.text = ("Scrub time:  {}".format(seconds-i))
        buzzer.duty_cycle = 0
        time.sleep(1)
    timer_label.text = ("Done!")
    wash_off_sprite.x = 0
    buzzer.duty_cycle = 2**15
    time.sleep(0.3)
    buzzer.duty_cycle = 0
    timer_label.x = 24
    timer_label.y = 100
    timer_label.text = ("Wave to start")

# setup buzzer
buzzer = pwmio.PWMOut(board.SPEAKER, variable_frequency=True)
buzzer.frequency = 1000

while True:
    # print("Distance: {}".format(clue.proximity))  # use to test the sensor
    if clue.proximity > 1:
        timer_label.x = 12
        timer_label.y = 226
        timer_label.text = "Scrub Away!"
        wash_off_sprite.x = 300
        time.sleep(2)
        countdown(20)
