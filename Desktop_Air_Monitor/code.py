# SPDX-FileCopyrightText: 2023 Liz Clark for Adafruit Industries
# SPDX-License-Identifier: MIT

import os
import ssl
import time
import microcontroller
import board
import wifi
import socketpool
import adafruit_requests
import neopixel
import displayio
from adafruit_ticks import ticks_ms, ticks_add, ticks_diff
from adafruit_io.adafruit_io import IO_HTTP, AdafruitIO_RequestError
from adafruit_pm25.i2c import PM25_I2C
import adafruit_scd4x
from adafruit_display_text import bitmap_label
from adafruit_bitmap_font import bitmap_font
from adafruit_display_shapes.roundrect import RoundRect

#  connect to SSID
wifi.radio.connect(os.getenv('CIRCUITPY_WIFI_SSID'), os.getenv('CIRCUITPY_WIFI_PASSWORD'))

pool = socketpool.SocketPool(wifi.radio)
requests = adafruit_requests.Session(pool, ssl.create_default_context())

pool = socketpool.SocketPool(wifi.radio)

# adafruit IO info
aio_username = os.getenv('aio_username')
aio_key = os.getenv('aio_key')
location = "America/New York"

# io HTTP for getting the time from the internet
io = IO_HTTP(aio_username, aio_key, requests)

def reset_on_error(delay, error):
    print("Error:\n", str(error))
    print("Resetting microcontroller in %d seconds" % delay)
    time.sleep(delay)
    microcontroller.reset()

def c_to_f(temp_data):
    temperature_celsius = temp_data
    temperature_fahrenheit = temperature_celsius * 9 / 5 + 32
    return int(temperature_fahrenheit)

# setup NeoPixels
pixel_pin = board.D13
num_pixels = 8

pixels = neopixel.NeoPixel(pixel_pin, num_pixels, brightness=0.3, auto_write=False)

red = (255, 0, 0)
yellow = (255, 125, 0)
green = (0, 255, 0)

i2c = board.STEMMA_I2C()

reset_pin = None

pm25 = PM25_I2C(i2c, reset_pin)
aqdata = pm25.read()

scd4x = adafruit_scd4x.SCD4X(i2c)
scd4x.start_periodic_measurement()

time.sleep(2)

co2 = int(scd4x.CO2)
temp = c_to_f(scd4x.temperature)
humidity = int(scd4x.relative_humidity)

pm2 = int(aqdata["pm25 standard"])
pm2_x = [94, 94, 94, 94, 140, 185]
pm2_colors = [green, green, green, green, yellow, red]

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

pm2_text = bitmap_label.Label(big_font, text="%d" % pm2, x=42, y=40, color=0xFFFFFF)
group.append(pm2_text)

co2_text = bitmap_label.Label(small_font, text="%d" % co2, x=50, y=107, color=0xFFFFFF)
temp_text = bitmap_label.Label(small_font, text="%d" % temp, x=130, y=107, color=0xFFFFFF)
humid_text = bitmap_label.Label(small_font, text="%d" % humidity, x=205, y=107, color=0xFFFFFF)
group.append(co2_text)
group.append(temp_text)
group.append(humid_text)

pm2_outline = RoundRect(pm2_x[pm2], 19, 46, 46, 10, fill=None, outline=0xFFFFFF, stroke=3)
group.append(pm2_outline)

pixels.fill(pm2_colors[pm2])
pixels.show()

display.show(group)

sensor_texts = [pm2_text, co2_text, temp_text, humid_text]
sensor_data = [pm2, co2, temp, humidity]

sensor_clock = ticks_ms()
io_clock = ticks_ms()

sensor_check = 30000
io_check = 300000
first_run = True

try:
    # get feed
    pm25_feed = io.get_feed("pm25")
except AdafruitIO_RequestError:
    # if no feed exists, create one
    pm25_feed = io.create_new_feed("pm25")
try:
    # get feed
    temp_feed = io.get_feed("temp")
except AdafruitIO_RequestError:
    # if no feed exists, create one
    temp_feed = io.create_new_feed("temp")
try:
    # get feed
    co2_feed = io.get_feed("co2")
except AdafruitIO_RequestError:
    # if no feed exists, create one
    co2_feed = io.create_new_feed("co2")
try:
    # get feed
    humid_feed = io.get_feed("humid")
except AdafruitIO_RequestError:
    # if no feed exists, create one
    humid_feed = io.create_new_feed("humid")

sensor_feeds = [pm25_feed, co2_feed, temp_feed, humid_feed]

while True:
    try:
        if first_run or ticks_diff(ticks_ms(), sensor_clock) > sensor_check:
            if scd4x.data_ready:
                co2 = int(scd4x.CO2)
                temp = c_to_f(scd4x.temperature)
                humidity = int(scd4x.relative_humidity)
            pm2 = int(aqdata["pm25 standard"])
            pm2_outline.x = pm2_x[pm2]
            pixels.fill(pm2_colors[pm2])
            pixels.show()
            for s in range(4):
                sensor_texts[s].text = "%d" % sensor_data[s]
                print("updated %d data" % sensor_data[s])
                time.sleep(0.2)
            sensor_clock = ticks_add(sensor_clock, sensor_check)

        if first_run or ticks_diff(ticks_ms(), io_clock) > io_check:
            for z in range(4):
                io.send_data(sensor_feeds[z]["key"], sensor_data[z])
                print("sent %d to io" % sensor_data[z])
                time.sleep(1)
            io_clock = ticks_add(io_clock, io_check)
        if first_run:
            sensor_clock = ticks_ms()
            io_clock = ticks_ms()
            first_run = False
    # pylint: disable=broad-except
    except Exception as e:
        reset_on_error(10, e)
