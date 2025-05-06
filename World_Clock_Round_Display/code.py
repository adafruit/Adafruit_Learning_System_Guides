# SPDX-FileCopyrightText: 2025 Ben Everard for Adafruit Industries
# 
# SPDX-License-Identifier: MIT
'''Display a world clock on a round LCD'''

import board
import os
import displayio
import fourwire
from adafruit_gc9a01a import GC9A01A
import time
import wifi
import adafruit_ntp
import adafruit_connection_manager

wifi.radio.connect(ssid=os.getenv('CIRCUITPY_WIFI_SSID'),
                   password=os.getenv('CIRCUITPY_WIFI_PASSWORD'))

pool = adafruit_connection_manager.get_radio_socketpool(wifi.radio)
ntp = adafruit_ntp.NTP(pool, tz_offset=0, cache_seconds=3600)

displayio.release_displays()
spi = board.SPI()
tft_cs = board.TX
tft_dc = board.RX

display_bus = fourwire.FourWire(
    spi, command=tft_dc, chip_select=tft_cs, reset=None
)

display = GC9A01A(display_bus, width=240, height=240, auto_refresh=False)

world = displayio.OnDiskBitmap("/world.bmp")

tile_grid_1 = displayio.TileGrid(world, pixel_shader=world.pixel_shader)
tile_grid_2 = displayio.TileGrid(world, pixel_shader=world.pixel_shader)

group = displayio.Group()

group.append(tile_grid_1)
group.append(tile_grid_2)
display.root_group = group

# Loop forever so you can enjoy your image
while True:
    tile_grid_1.x = (20*ntp.datetime.tm_hour)+120
    tile_grid_2.x = tile_grid_1.x-480
    display.refresh()
    time.sleep(60)
