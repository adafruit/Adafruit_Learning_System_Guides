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
bmp_file = "clean.bmp" if alarm.sleep_memory[0] else "dirty.bmp"

# show bitmap
with open(bmp_file, "rb") as fp:
    bitmap = displayio.OnDiskBitmap(fp)
    tile_grid = displayio.TileGrid(bitmap, pixel_shader=displayio.ColorConverter())
    group = displayio.Group(max_size=1)
    group.append(tile_grid)
    epd.show(group)
    time.sleep(epd.time_to_refresh + 0.01)
    epd.refresh()
    while epd.busy:
        pass

# go to sleep
alarm.exit_and_deep_sleep_until_alarms(*pin_alarms)
