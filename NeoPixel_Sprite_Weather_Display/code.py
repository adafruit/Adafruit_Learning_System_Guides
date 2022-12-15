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

# make the API request
response = requests.get(weather_url)
# packs the response into a JSON
response_as_json = response.json()
print()
# prints the entire JSON
print(response_as_json)
print()
# gets current weather code
weather = int(response_as_json['current_weather']['weathercode'])
print(weather)
# gets temperature
temp = response_as_json['current_weather']['temperature']
temp_int = int(temp)
print("%s°%s" % (temp, temp_unit))
# gets time
json_time = response_as_json['current_weather']['time']
new_time = json_time.rsplit("T", 1)[-1]
new_time = int(new_time[:2])
print(new_time)

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

# temperature for scrolling text
label = Label(text="   %s°%s   " % (temp, temp_unit), font=font)
bitmap = label.bitmap

# create 5x5 neopixels
pixels = neopixel.NeoPixel(board.A3, 5*5, brightness=.08, auto_write=False)
# count for pixels when drawing bitmaps
count = 0
# arrays to pack assets from weather_codes helper
# weather condition code
codes = []
# bitmap for daytime
day_images = []
# bitmap for nighttime
night_images = []

for i in weather_codes:
    codes.append(i['code'])
    day_images.append(i['day_img'])
    night_images.append(i['night_img'])

clock = time.monotonic()

# display current weather sprite & scroll temperature
while True:
    # check every hour
    if (time.monotonic() - clock) > 3600:
        # make the API request
        response = requests.get(weather_url)
        # packs the response into a JSON
        response_as_json = response.json()
        print()
        #  prints the entire JSON
        print(response_as_json)
        print()
        # current weather code
        weather = int(response_as_json['current_weather']['weathercode'])
        print(weather)
        # temperature
        temp = response_as_json['current_weather']['temperature']
        temp_int = int(temp)
        print("%s°%s" % (temp, temp_unit))
        # update scrolling text
        label.text = "   %s°%s   " % (temp, temp_unit)
        json_time = response_as_json['current_weather']['time']
        new_time = json_time.rsplit("T", 1)[-1]
        new_time = int(new_time[:2])
        print(new_time)
        clock = time.monotonic()
    # map color to temp range. colder temps are cool colors, warmer temps warm colors
    temp_color = simpleio.map_range(temp_int, min_temp, max_temp, 255, 0)
    # checks if it's day or night based on hour
    if new_time in range(daytime_min, daytime_max):
        img = day_images[weather]
    else:
        img = night_images[weather]
    # draw bitmap sprite
    for pixel in img:
        pixels[count] = pixel
        pixels.show()
        count+=1
        time.sleep(0.001)
    time.sleep(5)
    hue = 0
    count = 0
    # draw scrolling text
    for v in range(2):
        for i in range(bitmap.width):
            # Scoot the old text left by 1 pixel
            pixels[:20] = pixels[5:]
            # adjust color based on temperature
            color = colorwheel(temp_color)
            # Draw in the next line of text
            for y in range(5):
                # Select black or color depending on the bitmap pixel
                pixels[20+y] = color * bitmap[i,y]
            pixels.show()
            time.sleep(.1)
