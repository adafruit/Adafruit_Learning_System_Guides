# SPDX-FileCopyrightText: 2024 Liz Clark for Adafruit Industries
# SPDX-License-Identifier: MIT

import ssl
import os
import socketpool
import wifi
import board
import digitalio
import displayio
import vectorio
from adafruit_bitmap_font import bitmap_font
from adafruit_display_text import bitmap_label
import adafruit_imageload
from adafruit_io.adafruit_io import IO_HTTP, AdafruitIO_RequestError
import adafruit_max1704x
import adafruit_requests
from simpleio import map_range
from adafruit_ticks import ticks_ms, ticks_add, ticks_diff

# states
send_io = True
bat_clock = ticks_ms()
bat_timer = 60 * 1000
first_run = True
# settings.toml imports
aio_username = os.getenv('AIO_USERNAME')
aio_key = os.getenv('AIO_KEY')
# connect to wifi
wifi.radio.connect(os.getenv('CIRCUITPY_WIFI_SSID'), os.getenv('CIRCUITPY_WIFI_PASSWORD'))
pool = socketpool.SocketPool(wifi.radio)
requests = adafruit_requests.Session(pool, ssl.create_default_context())
io = IO_HTTP(aio_username, aio_key, requests)
try:
    # get feed
    battery_feed = io.get_feed("battery-monitor")
except AdafruitIO_RequestError:
    # if no feed exists, create one
    battery_feed = io.create_new_feed("battery-monitor")
# default group
group = displayio.Group()
# text only group
textOnly_group = displayio.Group()
board.DISPLAY.root_group = group
# palette for vector graphics
palette = displayio.Palette(5)
palette[0] = 0xFF0000
palette[1] = 0xFFFF00
palette[2] = 0x00FF00
palette[3] = 0x0000FF
palette[4] = 0x000000
# battery rectangle
rect = vectorio.Rectangle(pixel_shader=palette, width=72, height=45, x=140, y=70, color_index = 0)
group.append(rect)
text_bg = vectorio.Rectangle(pixel_shader=palette, width=115, height=70,
                             x=120, y=60, color_index = 4)
# io indicator circle
circle = vectorio.Circle(pixel_shader=palette, radius=8, x=10, y=10, color_index=3)
textOnly_group.append(circle)
# graphics bitmap
bitmap, palette_bit = adafruit_imageload.load(
    "/bat_bg.bmp",
    bitmap=displayio.Bitmap,
    palette=displayio.Palette,
)
# purple is made transparent
palette_bit.make_transparent(0)
tile_grid = displayio.TileGrid(bitmap, pixel_shader=palette_bit)
group.append(tile_grid)
group.append(circle)
# font for graphics
sm_file = "/roundedHeavy-26.bdf"
sm_font = bitmap_font.load_font(sm_file)
# font for text only
lg_file = "/roundedHeavy-46.bdf"
lg_font = bitmap_font.load_font(lg_file)
volt_text = bitmap_label.Label(sm_font, text=" V", x=150, y=33)
group.append(volt_text)
big_volt_text = bitmap_label.Label(lg_font, text=" V")
big_volt_text.anchor_point = (0.5, 0.0)
big_volt_text.anchored_position = (board.DISPLAY.width / 2, 0)
textOnly_group.append(big_volt_text)
percent_text = bitmap_label.Label(sm_font, text=" %", x=150, y=90)
big_percent_text = bitmap_label.Label(lg_font, text=" %", x=board.DISPLAY.width//2, y=90)
big_percent_text.anchor_point = (0.5, 1.0)
big_percent_text.anchored_position = (board.DISPLAY.width / 2, board.DISPLAY.height - 15)
textOnly_group.append(big_percent_text)

# buttons
button0 = digitalio.DigitalInOut(board.D0)
button0.direction = digitalio.Direction.INPUT
button0.pull = digitalio.Pull.UP
button0_state = False
button1 = digitalio.DigitalInOut(board.D1)
button1.direction = digitalio.Direction.INPUT
button1.pull = digitalio.Pull.DOWN
button1_state = False
button2 = digitalio.DigitalInOut(board.D2)
button2.direction = digitalio.Direction.INPUT
button2.pull = digitalio.Pull.DOWN
button2_state = False

# MAX17048 instantiation
monitor = adafruit_max1704x.MAX17048(board.I2C())
monitor.activity_threshold = 0.01

# colors for battery graphic
def get_color(value):
    if value < 30:
        return 0
    elif 30 <= value <= 75:
        return 1
    else:
        return 2

while True:
    # reset button state on release
    if button0.value and button0_state:
        button0_state = False
    if not button1.value and button1_state:
        button1_state = False
    if not button2.value and button2_state:
        button2_state = False
    # toggle sending to adafruit io
    if not button0.value and not button0_state:
        button0_state = True
        send_io = not send_io
        if send_io:
            circle.color_index = 3
        else:
            circle.color_index = 4
    # toggle graphics or text only
    if button1.value and not button1_state:
        button1_state = True
        if board.DISPLAY.root_group == group:
            board.DISPLAY.root_group = textOnly_group
        else:
            board.DISPLAY.root_group = group
    # toggle battery graphic or % text
    if button2.value and not button2_state:
        button2_state = True
        if len(group) > 4:
            group.pop()
            group.pop()
        else:
            group.append(text_bg)
            group.append(percent_text)
    # read MAX17048 every 60 seconds
    if first_run or ticks_diff(ticks_ms(), bat_clock) >= bat_timer:
        first_run = False
        battery_volts = monitor.cell_voltage
        battery_percent = monitor.cell_percent
        print(f"Battery voltage: {battery_volts:.2f} Volts")
        print(f"Battery percentage: {battery_percent:.1f} %")
        print()
        battery_display = map_range(battery_percent, 0, 100, 0, 72)
        battery_x = map_range(battery_percent, 0, 100, 210, 140)
        #  update rectangle to reflect battery charge
        rect.width = int(battery_display)
        rect.x = int(battery_x)
        rect.color_index = get_color(battery_percent)
        volt_text.text = f"{battery_volts:.2f} V"
        percent_text.text = f"{battery_percent:.1f} %"
        big_volt_text.text = f"{battery_volts:.2f} V"
        big_percent_text.text = f"{battery_percent:.1f} %"
        if battery_percent >= 100 and send_io:
            io.send_data(battery_feed["key"], battery_percent)
        bat_clock = ticks_add(bat_clock, bat_timer)
