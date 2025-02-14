# SPDX-FileCopyrightText: Copyright (c) 2024 Liz Clark for Adafruit Industries
#
# SPDX-License-Identifier: MIT

import busio
import board
from analogio import AnalogIn
import adafruit_st7789
import displayio
import neopixel
from rainbowio import colorwheel
from adafruit_display_text import label
from adafruit_ticks import ticks_ms, ticks_add, ticks_diff
from font_orbitron_bold_webfont_36 import FONT as orbitron_font

displayio.release_displays()
spi = busio.SPI(clock=board.GP18, MOSI=board.GP19)
display_bus = displayio.FourWire(spi, command=board.GP20, chip_select=board.GP21, reset=None)
display = adafruit_st7789.ST7789(display_bus, width=240, height=240, rowstart=80, rotation=0)

group = displayio.Group()
text = label.Label(orbitron_font, text="0V", color=0xFF0000)
text.anchor_point = (0.5, 0.5)
text.anchored_position = (display.width / 2, display.height / 2)
group.append(text)
display.root_group = group

analog_in = AnalogIn(board.A3)

def get_vsys(pin):
    return ((pin.value * 3) * 3.3) / 65535

pixel_pin = board.A2
num_pixels = 1
pixel = neopixel.NeoPixel(pixel_pin, num_pixels,
                           brightness=0.1, auto_write=True)
hue = 0
pixel.fill(colorwheel(hue))

bat_clock = ticks_ms()
bat_timer = 5000
neo_clock = ticks_ms()
neo_timer = 100

while True:
    if ticks_diff(ticks_ms(), bat_clock) >= bat_timer:
        print(f"The battery level is: {get_vsys(analog_in):.1f}V")
        text.text = f"{get_vsys(analog_in):.1f}V"
        text.color = colorwheel(hue)
        bat_clock = ticks_add(bat_clock, bat_timer)
    if ticks_diff(ticks_ms(), neo_clock) >= neo_timer:
        hue = (hue + 7) % 256
        pixel.fill(colorwheel(hue))
        neo_clock = ticks_add(neo_clock, neo_timer)
