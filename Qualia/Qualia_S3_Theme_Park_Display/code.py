# SPDX-FileCopyrightText: 2024 Liz Clark for Adafruit Industries
#
# SPDX-License-Identifier: MIT

import os
import ssl
import time
import microcontroller
import wifi
import socketpool
import adafruit_requests
import board
import displayio
import keypad
from adafruit_ticks import ticks_ms, ticks_add, ticks_diff
from adafruit_display_text import outlined_label
from adafruit_bitmap_font import bitmap_font
from adafruit_qualia.graphics import Graphics, Displays

urls = [{'name': "Epcot",
         'url': "https://queue-times.com/en-US/parks/5/queue_times.json"},
        {'name': "Magic Kingdom",
         'url': "https://queue-times.com/en-US/parks/6/queue_times.json"},
        {'name': "Hollywood Studios",
         'url': "https://queue-times.com/en-US/parks/7/queue_times.json"},
        {'name': "Animal Kingdom",
         'url': "https://queue-times.com/en-US/parks/8/queue_times.json"},
        ]
bitmap = displayio.OnDiskBitmap("/park-bg.bmp")

key = keypad.Keys((board.A0,), value_when_pressed=False, pull=True)

wifi.radio.connect(os.getenv("CIRCUITPY_WIFI_SSID"), os.getenv("CIRCUITPY_WIFI_PASSWORD"))
print(f"Connected to {os.getenv('CIRCUITPY_WIFI_SSID')}")

context = ssl.create_default_context()
pool = socketpool.SocketPool(wifi.radio)
requests = adafruit_requests.Session(pool, context)

graphics = Graphics(Displays.ROUND40, default_bg=None, auto_refresh=True)

grid = displayio.TileGrid(bitmap, pixel_shader=bitmap.pixel_shader)
group = displayio.Group()
group.append(grid)

font = bitmap_font.load_font("/Roboto-Regular-47.pcf")
ride_text = []
wait_text = []
for i in range(5):
    text_ride = outlined_label.OutlinedLabel(font, text=" ",
    outline_color=0x000000,
    outline_size=3,
    padding_left=4,
    padding_right=4,
    padding_top=4,
    padding_bottom=4)
    ride_text.append(text_ride)
    text_wait = outlined_label.OutlinedLabel(font, text=" ",
    outline_color=0x000000,
    outline_size=3,
    padding_left=4,
    padding_right=4,
    padding_top=4,
    padding_bottom=4)
    wait_text.append(text_wait)
    group.append(text_ride)
    group.append(text_wait)

text_park = outlined_label.OutlinedLabel(font, text=urls[0]['name'],
    outline_color = 0x000000,
    outline_size=3,
    padding_left=4,
    padding_right=4,
    padding_top=4,
    padding_bottom=4)
text_park.x = (graphics.display.width - text_park.width) // 2
text_park.y = graphics.display.height - (text_park.height * 2)
group.append(text_park)

def center(g, b):
    # center the image
    g.x -= (b.width - graphics.display.width) // 2
    g.y -= (b.height - graphics.display.height) // 2

center(grid, bitmap)

graphics.display.root_group = group

def sort_rides(data):
    y = 30
    x = [135, 55, 15, 25, 45]
    all_rides = []
    for land in data['lands']:
        all_rides.extend(land['rides'])
    sorted_rides = sorted(all_rides, key=lambda x: x['wait_time'], reverse=True)
    for ride in sorted_rides:
        r = sorted_rides.index(ride)
        if r > 4:
            break
        #print(wait_text[r])
        ride_text[r].text = f"{ride['name']:.20}"
        if len(ride['name']) > 20:
            ride_text[r].text = ride_text[r].text + ".."
        ride_text[r].x = x[r]
        ride_text[r].y = y + 70
        wait_text[r].text = f"{ride['wait_time']} Minutes"
        wait_text[r].x = 400
        wait_text[r].y = ride_text[r].y + wait_text[r].height + 20
        y += wait_text[r].height * 2 + 30

clock_timer = 5 * 60 * 1000
clock_clock = ticks_ms()
park_index = 0
update = True

while True:
    try:
        event = key.events.get()
        if event:
            if event.pressed:
                print("updating display")
                park_index = (park_index + 1) % len(urls)
                text_park.text=urls[park_index]['name']
                text_park.x = (graphics.display.width - text_park.width) // 2
                text_park.y = graphics.display.height - (text_park.height * 2)
                update = True
        if ticks_diff(ticks_ms(), clock_clock) >= clock_timer or update:
            response = requests.get(urls[park_index]['url'])
            #  packs the response into a JSON
            response_data = response.json()
            sort_rides(response_data)
            update = False
            clock_clock = ticks_add(clock_clock, clock_timer)
    except Exception as error: # pylint: disable=broad-except
        print(f"error! {error} resetting..")
        time.sleep(5)
        microcontroller.reset()
