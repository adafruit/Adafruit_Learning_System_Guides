# SPDX-FileCopyrightText: 2025 Liz Clark for Adafruit Industries
#
# SPDX-License-Identifier: MIT

import os
import time
import ssl
import board
import wifi
import socketpool
import microcontroller
import displayio
from adafruit_display_text.bitmap_label import Label
from adafruit_bitmap_font import bitmap_font
import adafruit_imageload
from fourwire import FourWire
import adafruit_requests
from adafruit_gc9a01a import GC9A01A
from adafruit_ticks import ticks_ms, ticks_add, ticks_diff

cad_url = ("https://ssd-api.jpl.nasa.gov/cad.api?"
            "des=2024%20YR4&body=ALL&"
            "date-min=2030-01-01&date-max=2060-01-01")
sentry_url = "https://ssd-api.jpl.nasa.gov/sentry.api?des=2024%20YR4"
# connect to wifi
try:
    wifi.radio.connect(os.getenv('CIRCUITPY_WIFI_SSID'), os.getenv('CIRCUITPY_WIFI_PASSWORD'))
except TypeError:
    print("Could not find WiFi info. Check your settings.toml file!")
    raise
context = ssl.create_default_context()
with open("/ssd-api-jpl-nasa-gov-chain.pem", "rb") as certfile:
    context.load_verify_locations(cadata=certfile.read())

pool = socketpool.SocketPool(wifi.radio)
requests = adafruit_requests.Session(pool, context)

spi = board.SPI()
tft_cs = board.TX
tft_dc = board.RX
tft_reset = None

displayio.release_displays()

display_bus = FourWire(spi, command=tft_dc, chip_select=tft_cs, reset=tft_reset)
display = GC9A01A(display_bus, width=240, height=240, auto_refresh=False)

main_group = displayio.Group()
display.root_group = main_group

bitmap_bg, palette_bg = adafruit_imageload.load("/earth_bg.bmp",
                                          bitmap=displayio.Bitmap,
                                          palette=displayio.Palette)

grid_bg = displayio.TileGrid(bitmap_bg, pixel_shader=palette_bg)
main_group.append(grid_bg)

font = bitmap_font.load_font('/Arial-14.bdf')
name_area = Label(font, text="2024 YR4", color=0xFFFFFF, background_color=0x000000)
name_area.anchored_position = (display.width / 2, 0)
name_area.anchor_point = (0.5, 0.0)

date_area = Label(font, text="2032-12-22", color=0xFFFFFF, background_color=0x000000)
date_area.anchored_position = (display.width / 2, name_area.height+10)
date_area.anchor_point = (0.5, 0.0)

moon_area = Label(font, text="Moon: ", color=0xFFFFFF, background_color=0x000000)
moon_area.anchored_position = (display.width / 2, name_area.height+10 + date_area.height+5)
moon_area.anchor_point = (0.5, 0.0)

earth_area = Label(font, text="Earth: ", color=0xFFFFFF, background_color=0x000000)
earth_area.anchored_position = (display.width / 2, name_area.height+10 +
                                                   moon_area.height+5 +
                                                   date_area.height + 5)
earth_area.anchor_point = (0.5, 0.0)

impact_area = Label(font, text="Earth Impact: 0.0000%", color=0xFFFFFF, background_color=0x000000)
impact_area.anchored_position = (display.width / 2, name_area.height+10 +
                                                    moon_area.height+5 +
                                                    earth_area.height + 5 +
                                                    date_area.height + 5)
impact_area.anchor_point = (0.5, 0.0)
main_group.append(impact_area)
main_group.append(earth_area)
main_group.append(moon_area)
main_group.append(date_area)
main_group.append(name_area)

bit_asteroid, pal_asteroid = adafruit_imageload.load("/asteroid.bmp",
                                          bitmap=displayio.Bitmap,
                                          palette=displayio.Palette)

asteroid = displayio.TileGrid(bit_asteroid, pixel_shader=pal_asteroid,
							  x = 25, y=100)
pal_asteroid.make_transparent(0)
main_group.append(asteroid)

def diagonal_travel(bitmap_object, start_x=-59, start_y=-59, end_x=240, end_y=240, delay=0.01):
    # Set initial position
    bitmap_object.x = start_x
    bitmap_object.y = start_y

    # Calculate total movement distance
    distance_x = end_x - start_x
    distance_y = end_y - start_y

    # Calculate number of steps (use the larger distance)
    steps = max(abs(distance_x), abs(distance_y)) // 1

    # Calculate step size for each axis to maintain diagonal movement
    step_x = distance_x / steps
    step_y = distance_y / steps

    # Animate the movement
    for i in range(steps + 1):
        # Update position
        bitmap_object.x = int(start_x + (step_x * i))
        bitmap_object.y = int(start_y + (step_y * i))
        display.refresh()
        # Pause to control animation speed
        time.sleep(delay)

def au_to_miles(au):
    # 1 AU = 92,955,807 miles
    miles_per_au = 92955807

    return au * miles_per_au

timer_clock = ticks_ms()
timer = 3600 * 1000
first_run = True

while True:
    try:
        if first_run or ticks_diff(ticks_ms(), timer_clock) >= timer:
            sentry_response = requests.get(sentry_url)
            sentry_json = sentry_response.json()
            impact = sentry_json['summary']['ip']
            sentry_response.close()
            overall_ip = float(impact) * 100
            cad_response = requests.get(cad_url)
            cad_json = cad_response.json()
            earth_distance = au_to_miles(float(cad_json['data'][0][4]))
            earth_area.text = f"{cad_json['data'][0][10]}: {int(earth_distance)} mi"
            moon_distance = au_to_miles(float(cad_json['data'][1][4]))
            moon_area.text = f"{cad_json['data'][1][10]}: {int(moon_distance)} mi"
            date = cad_json['data'][0][3]
            date = date.split()
            date_area.text = f"{date[0]}"
            cad_response.close()
            impact_area.text = f"Earth Impact: {overall_ip:.4f}%"
            display.refresh()
            timer_clock = ticks_add(timer_clock, timer)
        diagonal_travel(asteroid, start_x=-45, start_y=300, end_x=300, end_y=-45)
        time.sleep(0.1)
    # pylint: disable=broad-except
    except Exception as e:
        print("Error:\n", str(e))
        print("Resetting microcontroller in 10 seconds")
        time.sleep(10)
        microcontroller.reset()
