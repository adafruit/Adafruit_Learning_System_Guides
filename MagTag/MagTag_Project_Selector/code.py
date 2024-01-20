# SPDX-FileCopyrightText: 2020 Eva Herrada for Adafruit Industries
#
# SPDX-License-Identifier: MIT

# Based on code written by @DavidGlaude on Twitter
# https://twitter.com/DavidGlaude/status/1340365817138044933
# https://gist.github.com/dglaude/4bf8d0a13c9c8ca8b05d6c0e9176bd20

import time
import alarm
import displayio
import board
import adafruit_imageload
from adafruit_display_shapes.rect import Rect
from adafruit_magtag.magtag import Graphics
from digitalio import DigitalInOut, Direction, Pull

projects = [
    "weather",
    "spacex",
    "covid",
    "showerthoughts",
    "tides",
    "year",
    "showtimes",
    "slideshow",
]

btnA = DigitalInOut(board.D15)
btnA.direction = Direction.INPUT
btnA.pull = Pull.UP

btnB = DigitalInOut(board.D14)
btnB.direction = Direction.INPUT
btnB.pull = Pull.UP

btnC = DigitalInOut(board.D12)
btnC.direction = Direction.INPUT
btnC.pull = Pull.UP

btnD = DigitalInOut(board.D11)
btnD.direction = Direction.INPUT
btnD.pull = Pull.UP

graphics = Graphics(auto_refresh=False)
display = graphics.display
group = displayio.Group()

selector = False
if not btnA.value or not btnB.value or not btnC.value or not btnD.value:
    selector = True

if selector:
    background = Rect(0, 0, 296, 128, fill=0xFFFFFF)
    group.append(background)
    for i in range(8):
        sprite_sheet, palette = adafruit_imageload.load(
            f"/bmps/{projects[i]}.bmp",
            bitmap=displayio.Bitmap,
            palette=displayio.Palette,
        )
        sprite = displayio.TileGrid(
            sprite_sheet,
            pixel_shader=palette,
            width=1,
            height=1,
            tile_width=62,
            tile_height=54,
            x=6 + 74 * (i % 4),
            y=6 + 62 * (i // 4),
        )
        group.append(sprite)

    rect = Rect(4, 4, 66, 58, outline=0x000000, stroke=2)
    group.append(rect)
    display.root_group = group
    display.refresh()

    time.sleep(5)
    print("Ready")
    selected = 0
    while True:
        if not btnA.value and not btnD.value:
            alarm.sleep_memory[0] = selected
            break

        if not btnA.value and selected != 0 and selected != 4:
            selected -= 1
            rect.x -= 74
            display.refresh()
            print("left")
            time.sleep(5)
            continue

        if not btnB.value and selected > 3:
            selected -= 4
            rect.y -= 62
            display.refresh()
            print("up")
            time.sleep(5)
            continue

        if not btnC.value and selected < 4:
            selected += 4
            rect.y += 62
            display.refresh()
            print("down")
            time.sleep(5)
            continue

        if not btnD.value and selected != 3 and selected != 7:
            selected += 1
            rect.x += 74
            display.refresh()
            print("right")
            time.sleep(5)
            continue

btnA.deinit()
btnB.deinit()
btnC.deinit()
btnD.deinit()

print("Starting ", projects[int(alarm.sleep_memory[0])])
__import__("/projects/" + projects[int(alarm.sleep_memory[0])])
