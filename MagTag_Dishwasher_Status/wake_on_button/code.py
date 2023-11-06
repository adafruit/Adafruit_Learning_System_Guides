# SPDX-FileCopyrightText: 2021 Carter Nelson for Adafruit Industries
#
# SPDX-License-Identifier: MIT

import time
import board
import alarm
import displayio

# get the display
epd = board.DISPLAY
epd.rotation = 270

# set up pin alarms
buttons = (board.BUTTON_A, board.BUTTON_B)  # pick any two
pin_alarms = [alarm.pin.PinAlarm(pin=pin, value=False, pull=True) for pin in buttons]

# toggle saved state
alarm.sleep_memory[0] = not alarm.sleep_memory[0]

# set bitmap
bmp_file = "/images/clean.bmp" if alarm.sleep_memory[0] else "/images/dirty.bmp"

# show bitmap

# CircuitPython 6 & 7 compatible
with open(bmp_file, "rb") as fp:
    bitmap = displayio.OnDiskBitmap(fp)
    tile_grid = displayio.TileGrid(
        bitmap, pixel_shader=getattr(bitmap, 'pixel_shader', displayio.ColorConverter())
    )
    group = displayio.Group()
    group.append(tile_grid)
    epd.root_group = group
    time.sleep(epd.time_to_refresh + 0.01)
    epd.refresh()
    while epd.busy:
        pass

# # CircuitPython 7+ compatible
# bitmap = displayio.OnDiskBitmap(bmp_file)
# tile_grid = displayio.TileGrid(bitmap, pixel_shader=bitmap.pixel_shader)
# group = displayio.Group()
# group.append(tile_grid)
# epd.root_group = group
# time.sleep(epd.time_to_refresh + 0.01)
# epd.refresh()
# while epd.busy:
#     pass

# go to sleep
alarm.exit_and_deep_sleep_until_alarms(*pin_alarms)
