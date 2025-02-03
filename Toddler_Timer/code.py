# SPDX-FileCopyrightText: 2025 Liz Clark for Adafruit Industries
#
# SPDX-License-Identifier: MIT

import time
import board
import displayio
import neopixel
import digitalio
from adafruit_seesaw import seesaw, rotaryio, digitalio
from adafruit_bitmap_font import bitmap_font
from adafruit_display_text import label
import adafruit_displayio_ssd1306
import simpleio
from adafruit_ticks import ticks_ms, ticks_add, ticks_diff
from rainbowio import colorwheel

COLOR = (255, 150, 0)  # yellow
OFF = (0, 0, 0)
PIXEL_PIN = board.A0
NUM_PIXELS = 6
timers = [6, 10, 15, 20, 25, 30]  # minutes
color_time = 20  # milliseconds

# rotary encoder
i2c = board.STEMMA_I2C()
seesaw = seesaw.Seesaw(i2c, addr=0x36)
encoder = rotaryio.IncrementalEncoder(seesaw)
pos = -encoder.position
last_pos = pos
seesaw.pin_mode(24, seesaw.INPUT_PULLUP)
button = digitalio.DigitalIO(seesaw, 24)
button_state = False

pixels = neopixel.NeoPixel(PIXEL_PIN, NUM_PIXELS, brightness=0.2, auto_write=False)
pixels.fill(OFF)
pixels.show()

# display setup
displayio.release_displays()

# oled
oled_reset = board.D9
display_bus = displayio.I2CDisplay(i2c, device_address=0x3D, reset=oled_reset)
WIDTH = 128
HEIGHT = 64
display = adafruit_displayio_ssd1306.SSD1306(display_bus, width=WIDTH, height=HEIGHT)

font = bitmap_font.load_font("/Arial-14.bdf")
main_area = label.Label(font, text="6 Minutes", color=0xFFFFFF)
main_area.anchor_point = (0.5, 0.0)
main_area.anchored_position = (display.width / 2, display.height / 2)
splash = displayio.Group()
splash.append(main_area)
display.root_group = splash

timer_index = 0
timer = timers[timer_index]
time_remaining = timer * 60000
active_timer = False
timer_clock = ticks_ms()
color_clock = ticks_ms()
color_value = 0
last_map = 0
mapped_time = 0

while True:
    if not active_timer:
        pos = encoder.position
        if pos != last_pos:
            if pos > last_pos:
                timer_index = (timer_index + 1) % 6
            else:
                timer_index = (timer_index - 1) % 6
            print(timer_index)
            main_area.text = f"{timers[timer_index]} Minutes"
            last_pos = pos
        if not button.value and not button_state:
            main_area.text = "START!"
            timer = timers[timer_index]
            time_remaining = timer * 60000
            last_map = 0
            timer_clock = ticks_ms()
            color_clock = ticks_ms()
            active_timer = True
            button_state = True
        if button.value and button_state:
            button_state = False
    if active_timer:
        if ticks_diff(ticks_ms(), timer_clock) >= 1000:
            time_remaining -= 1000
            remaining = int(time_remaining / 1000)
            secs_remaining = remaining % 60
            remaining //= 60
            mins_remaining = remaining % 60
            if time_remaining > 0:
                mapped_time = simpleio.map_range(
                    time_remaining, 0, (timer * 60000), 0, NUM_PIXELS + 1
                )
                if mapped_time < 1:
                    mapped_time = 1
                if int(mapped_time) != last_map:
                    pixels.fill(OFF)
                    last_map = int(mapped_time)
                main_area.text = f"{mins_remaining}:{secs_remaining:02}"
            else:
                pixels.fill(COLOR)
                pixels.show()
                time.sleep(0.5)
                pixels.fill(OFF)
                pixels.show()
                main_area.text = "DONE!"
            print(time_remaining)
            timer_clock = ticks_add(timer_clock, 1000)
        if ticks_diff(ticks_ms(), color_clock) >= color_time:
            color_value = (color_value + 1) % 255
            for i in range(int(mapped_time)):
                pixels[i] = colorwheel(color_value)
            if time_remaining > 0:
                pixels.show()
            color_clock = ticks_add(color_clock, color_time)
        if not button.value and not button_state:
            timer = timers[timer_index]
            pixels.fill(OFF)
            pixels.show()
            main_area.text = "STOPPED"
            active_timer = False
            button_state = True
        if button.value and button_state:
            button_state = False
