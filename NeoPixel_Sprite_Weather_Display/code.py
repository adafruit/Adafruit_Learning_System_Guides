# SPDX-FileCopyrightText: 2022 Liz Clark for Adafruit Industries
# SPDX-License-Identifier: MIT

import os
import ssl
import time
import board
import wifi
import socketpool
import fontio
import neopixel
import simpleio
from adafruit_display_text.bitmap_label import Label
from adafruit_bitmap_font import bitmap_font
from displayio import Bitmap
from rainbowio import colorwheel
from adafruit_ticks import ticks_ms, ticks_add, ticks_diff
import adafruit_requests
from weather_codes import weather_codes

# minimum expected temperature
min_temp = 0
# maximum expected temperature
max_temp = 100
# first daylight hour
daytime_min = 7
# last daylight hour
daytime_max = 17
# latitude
lat = 42.36
# longitude
long = -71.06
# temp unit for API request
temperature_unit = "fahrenheit"
# temp unit for display
temp_unit = "F"

# API request to open-meteo
weather_url = "https://api.open-meteo.com/v1/forecast?"
# pass latitude and longitude
weather_url += "latitude=%d&longitude=%d&timezone=auto" % (lat, long)
# pass temperature_unit
weather_url += "&current_weather=true&temperature_unit=%s&windspeed_unit=mph" % temperature_unit

#  connect to SSID
wifi.radio.connect(os.getenv('WIFI_SSID'), os.getenv('WIFI_PASSWORD'))

pool = socketpool.SocketPool(wifi.radio)
requests = adafruit_requests.Session(pool, ssl.create_default_context())

def get_the_weather():
    # make the API request
    response = requests.get(weather_url)
    # packs the response into a JSON
    response_as_json = response.json()
    print()
    # prints the entire JSON
    print(response_as_json)
    print()
    # gets current weather code
    w = int(response_as_json['current_weather']['weathercode'])
    # gets temperature
    t = response_as_json['current_weather']['temperature']
    temp_int = int(t)
    t_c = simpleio.map_range(temp_int, min_temp, max_temp, 255, 0)
    # gets time
    json_time = response_as_json['current_weather']['time']
    n_t = json_time.rsplit("T", 1)[-1]
    n_t = int(n_t[:2])
    return w, t, t_c, n_t

# initial API call
weather, temp, temp_color, new_time = get_the_weather()

# font edit code by Jeff Epler
tom_thumb = bitmap_font.load_font("tom-thumb.pcf", Bitmap)

_glyph_keys = ['bitmap', 'tile_index', 'width', 'height', 'dx', 'dy', 'shift_x', 'shift_y']
def patch_glyph(base, **kw):
    d = {}
    for k in _glyph_keys:
        d[k] = kw.get(k, getattr(base, k))
    return fontio.Glyph(**d)

class PatchedFont:
    def __init__(self, base_font, patches):
        self.base_font = base_font
        self.patches = patches

    def get_glyph(self, glyph):
        g = self.base_font.get_glyph(glyph)
        patch = self.patches.get(glyph)
        if patch is not None:
            #print("patching", repr(chr(glyph)), g)
            g = patch_glyph(g, **patch)
            #print("patched", g)
        return g

    def get_bounding_box(self):
        return self.base_font.get_bounding_box()

font = PatchedFont(tom_thumb,
    {
        32: {'shift_x': 1, 'dx': 0},
        105: {'dx': 0, 'shift_x': 2},
        33: {'dx': 0, 'shift_x': 2},
    })
# thank you Jeff for this PatchedFont() function!

# temperature for scrolling text
label = Label(text="   %s°%s   " % (temp, temp_unit), font=font)
text = label.bitmap

# create 5x5 neopixels
pixels = neopixel.NeoPixel(board.A3, 5*5, brightness=.08, auto_write=False)
# count for pixels when drawing bitmaps
count = 0
# arrays to pack assets from weather_codes helper
# weather condition code
codes = []
# bitmaps for daytime
day_images = []
# bitmaps for nighttime
night_images = []

for i in weather_codes:
    codes.append(i['code'])
    day_images.append(i['day_img'])
    night_images.append(i['night_img'])

# checks if it's day or night based on hour
def day_or_night(t):
    if t in range(daytime_min, daytime_max):
        z = day_images[weather]
    else:
        z = night_images[weather]
    return z

# initial sprite selection
img = day_or_night(new_time)

# draw bitmap sprite
def draw_sprite(c):
    for pixel in img:
        pixels[c] = pixel
        pixels.show()
        c += 1
        time.sleep(0.001)
    c = 0

# ticks time tracker
clock = ticks_ms()

# 15 minutes in milliseconds
weather_check = 900000

# display current weather sprite & scroll temperature
while True:
    # checks the time
    if ticks_diff(ticks_ms(), clock) > weather_check:
        print("pinging Open-Meteo")
        # make the API request with function
        # return weather ID, temp, temp color & hour
        weather, temp, temp_color, new_time = get_the_weather()
        # checks if it's day or night based on hour
        # & returns day or night version of sprite
        img = day_or_night(new_time)
        # reset clock
        clock = ticks_add(clock, weather_check)
    # draw bitmap sprite
    draw_sprite(count)
    # blocking delay to hold the sprite on the display
    time.sleep(5)
    # draw scrolling text
    for v in range(2):
        for i in range(text.width):
            # Scoot the old text left by 1 pixel
            pixels[:20] = pixels[5:]
            # adjust color based on temperature
            color = colorwheel(temp_color)
            # Draw in the next line of text
            for y in range(5):
                # Select black or color depending on the bitmap pixel
                pixels[20+y] = color * text[i,y]
            pixels.show()
            time.sleep(.1)
