# SPDX-FileCopyrightText: 2023 Liz Clark for Adafruit Industries
# SPDX-License-Identifier: MIT

import time
import board
import neopixel
import displayio
from adafruit_ticks import ticks_ms, ticks_add, ticks_diff
from adafruit_pm25.i2c import PM25_I2C
import adafruit_scd4x
from adafruit_display_text import bitmap_label
from adafruit_bitmap_font import bitmap_font
from adafruit_display_shapes.roundrect import RoundRect

pixel_pin = board.D13
num_pixels = 8

pixels = neopixel.NeoPixel(pixel_pin, num_pixels, brightness=0.1, auto_write=False)

red = (80, 0, 0)
yellow = (75, 80, 0)
green = (0, 80, 0)

i2c = board.STEMMA_I2C()

reset_pin = None

pm25 = PM25_I2C(i2c, reset_pin)

scd4x = adafruit_scd4x.SCD4X(i2c)
scd4x.start_periodic_measurement()

time.sleep(5)

try:
    aqdata = pm25.read()
    pm2 = int(aqdata["pm25 standard"])
except RuntimeError:
    pm2 = 0

co2 = scd4x.CO2
temp = scd4x.temperature
humidity = scd4x.relative_humidity

def rate_pm25(pm25_data):
    if pm25_data <= 12:
        pm25_outline = 94
        pm25_color = green
    elif pm25_data <= 35:
        pm25_color = yellow
        pm25_outline = 140
    else:
        pm25_color = red
        pm25_outline = 185
    return pm25_color, pm25_outline

def c_to_f(temp_data):
    temperature_celsius = temp_data
    temperature_fahrenheit = temperature_celsius * 9 / 5 + 32
    return temperature_fahrenheit

#  display setup
display = board.DISPLAY

bitmap = displayio.OnDiskBitmap("/airBG.bmp")

tile_grid = displayio.TileGrid(bitmap, pixel_shader=bitmap.pixel_shader)
group = displayio.Group()
group.append(tile_grid)

small_font_file = "/OCRA_small.pcf"
small_font = bitmap_font.load_font(small_font_file)
big_font_file = "/OCRA_big.pcf"
big_font = bitmap_font.load_font(big_font_file)

pm2_text = bitmap_label.Label(big_font, text="%d" % pm2, x=37, y=40, color=0xFFFFFF)
group.append(pm2_text)

co2_text = bitmap_label.Label(small_font, text="%d" % co2, x=50, y=107, color=0xFFFFFF)
temp_text = bitmap_label.Label(small_font, text="%d" % temp, x=130, y=107, color=0xFFFFFF)
humid_text = bitmap_label.Label(small_font, text="%d" % humidity, x=205, y=107, color=0xFFFFFF)
group.append(co2_text)
group.append(temp_text)
group.append(humid_text)

pm2_outline = RoundRect(94, 19, 46, 46, 10, fill=None, outline=0xFFFFFF, stroke=3)
group.append(pm2_outline)

display.root_group = group

sensor_texts = [pm2_text, co2_text, temp_text, humid_text]
sensor_data = [pm2, co2, temp, humidity]

sensor_clock = ticks_ms()

sensor_check = 5000
first_run = True

while True:
    if first_run or ticks_diff(ticks_ms(), sensor_clock) > sensor_check:
        co2 = scd4x.CO2
        temp = c_to_f(scd4x.temperature)
        humidity = scd4x.relative_humidity
        try:
            aqdata = pm25.read()
            pm2 = int(aqdata["pm25 standard"])
        except RuntimeError:
            print("Unable to read from PM2.5 sensor, no new data..")
            continue
        pm2_color, pm2_outline.x = rate_pm25(pm2)
        sensor_data = [pm2, co2, temp, humidity]
        pixels.fill(pm2_color)
        pixels.show()
        for s in range(4):
            sensor_texts[s].text = "%d" % sensor_data[s]
            print("updated %d data" % sensor_data[s])
            time.sleep(0.2)
        sensor_clock = ticks_add(sensor_clock, sensor_check)

    if first_run:
        sensor_clock = ticks_ms()
        first_run = False
