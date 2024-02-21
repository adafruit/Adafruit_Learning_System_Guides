# SPDX-FileCopyrightText: 2023 Liz Clark for Adafruit Industries
# SPDX-License-Identifier: MIT

import time
import ssl
import os
import json
import socketpool
import wifi
import board
import digitalio
import terminalio
import adafruit_requests
from adafruit_io.adafruit_io import IO_HTTP, AdafruitIO_RequestError
import displayio
from adafruit_progressbar.horizontalprogressbar import (
    HorizontalProgressBar,
    HorizontalFillDirection,
)
from adafruit_display_shapes.rect import Rect
from adafruit_display_text import bitmap_label,  wrap_text_to_lines
import neopixel
from adafruit_led_animation.animation.rainbow import Rainbow
from adafruit_led_animation.animation.blink import Blink

aio_username = os.getenv('aio_username')
aio_key = os.getenv('aio_key')

wifi.radio.connect(os.getenv('CIRCUITPY_WIFI_SSID'), os.getenv('CIRCUITPY_WIFI_PASSWORD'))

# Make the display context
splash = displayio.Group()
board.DISPLAY.root_group = splash

# set progress bar width and height relative to board's display
width = 183
height = 30

x = 50
#y = board.DISPLAY.height // 3
y = 100

# Create a new progress_bar object at (x, y)
progress_bar = HorizontalProgressBar(
    (x, y),
    (width, height),
    fill_color=0x000000,
    outline_color=0xFFFFFF,
    bar_color=0x13c100,
    direction=HorizontalFillDirection.LEFT_TO_RIGHT
)

# Append progress_bar to the splash group
splash.append(progress_bar)

rect = Rect(40, 0, 2, 135, fill=0xFFFFFF)
splash.append(rect)

img = displayio.OnDiskBitmap("octoprint_logo.bmp")
idle_icons = displayio.OnDiskBitmap("idle_icons.bmp")
printing_icons = displayio.OnDiskBitmap("printing_icons.bmp")
finished_icon = displayio.OnDiskBitmap("finished_icon.bmp")

tile_grid = displayio.TileGrid(bitmap=img, pixel_shader=img.pixel_shader, x = 185, y=5)
splash.append(tile_grid)

icon_grid = displayio.TileGrid(bitmap=idle_icons, pixel_shader=idle_icons.pixel_shader, x = 0, y=0)
splash.append(icon_grid)

text = bitmap_label.Label(terminalio.FONT, text="Connecting", scale=2, x=55, y=45)
splash.append(text)

led = digitalio.DigitalInOut(board.LED)
led.direction = digitalio.Direction.OUTPUT

button0 = digitalio.DigitalInOut(board.D0)
button0.direction = digitalio.Direction.INPUT
button0.pull = digitalio.Pull.UP

button1 = digitalio.DigitalInOut(board.D1)
button1.direction = digitalio.Direction.INPUT
button1.pull = digitalio.Pull.DOWN

button2 = digitalio.DigitalInOut(board.D2)
button2.direction = digitalio.Direction.INPUT
button2.pull = digitalio.Pull.DOWN
# Our array of key objects
button0_state = False
button1_state = False
button2_state = False

pixel = neopixel.NeoPixel(board.NEOPIXEL, 1, brightness = 0.6)

# Create a socket pool
pool = socketpool.SocketPool(wifi.radio)

requests = adafruit_requests.Session(pool, ssl.create_default_context())
# Initialize an Adafruit IO HTTP API object
io = IO_HTTP(aio_username, aio_key, requests)

try:
    # get feed
    # printing monitors the printer progress feed
    printing_status = io.get_feed("printing")
except AdafruitIO_RequestError:
    # if no feed exists, create one
    printing_status = io.create_new_feed("printing")
try:
    print_done = io.get_feed("printdone")
except AdafruitIO_RequestError:
    print_done = io.create_new_feed("printdone")
try:
    printer_state = io.get_feed("printerstatechanged")
except AdafruitIO_RequestError:
    printer_state = io.create_new_feed("printerstatechanged")
try:
    shutdown = io.get_feed("shutdown")
except AdafruitIO_RequestError:
    shutdown = io.create_new_feed("shutdown")
try:
    heat_up = io.get_feed("heatup")
except AdafruitIO_RequestError:
    heat_up = io.create_new_feed("heatup")
try:
    cooldown = io.get_feed("cooldown")
except AdafruitIO_RequestError:
    cooldown = io.create_new_feed("cooldown")
try:
    resume = io.get_feed("printresumed")
except AdafruitIO_RequestError:
    resume = io.create_new_feed("printresumed")
try:
    pause = io.get_feed("printpaused")
except AdafruitIO_RequestError:
    pause = io.create_new_feed("printpaused")
try:
    cancelled = io.get_feed("printcancelled")
except AdafruitIO_RequestError:
    cancelled = io.create_new_feed("printcancelled")

read_feeds = [printing_status, printer_state, print_done]
send_while_idle_feeds = [cooldown, heat_up, shutdown]
send_while_printing_feeds = [pause, resume, cancelled]
new_feed_msg = ["None", "None", "None"]
last_feed_msg = ["none","none","none"]
msg_json = [{"path": "none"}, {"state_id": "NONE"}, {"path": "none"}]
print_progress = 0
current_state = 0
last_state = None
state_value = 0
current_file = None
finished_file = None
red = (255, 0, 0)
green = (0, 255, 0)
blue = (0, 0, 255)
cyan = (0, 255, 255)
purple = (255, 0, 255)
yellow = (255, 255, 0)

printer_state_options = ["OPEN_SERIAL", "DETECT_SERIAL",
"DETECT_BAUDRATE", "CONNECTING", "OPERATIONAL", "PRINTING", "PAUSING", "PAUSED",
"CLOSED", "ERROR", "FINISHING", "CLOSED_WITH_ERROR", "TRANSFERING_FILE", "OFFLINE", "STARTING",
"CANCELLING", "UNKNOWN", "NONE"]
colors = [green, yellow, cyan, yellow,
          green, purple, yellow, yellow, red,
          red, blue, red, yellow, red,
          purple, red, red, red]

clock = 5

rainbow = Rainbow(pixel, speed=0.1, period=2)
blink = Blink(pixel, speed=0.5, color=green)

while True:
    if button0.value and button0_state:
        led.value = False
        button0_state = False
    if not button1.value and button1_state:
        led.value = False
        button1_state = False
    if not button2.value and button2_state:
        led.value = False
        button2_state = False

    if current_state in ("PRINTING", "PAUSED", "PAUSING"):
        rainbow.animate()
        if not button0.value and not button0_state:
            led.value = True
            io.send_data(send_while_printing_feeds[0]["key"], "ping")
            button0_state = True
        if button1.value and not button1_state:
            led.value = True
            io.send_data(send_while_printing_feeds[1]["key"], "ping")
            button1_state = True
        if button2.value and not button2_state:
            led.value = True
            io.send_data(send_while_printing_feeds[2]["key"], "ping")
            button2_state = True
    else:
        blink.color=colors[state_value]
        blink.animate()
        if not button0.value and not button0_state:
            if finished_file == current_file:
                current_file = "None"
                progress_bar.value = 100
                progress_bar.bar_color = colors[state_value]
                text.text = "\n".join(wrap_text_to_lines("Status: %s" % current_state, 11))
                icon_grid.bitmap = idle_icons
                icon_grid.pixel_shader = idle_icons.pixel_shader
                button0_state = True
            else:
                led.value = True
                io.send_data(send_while_idle_feeds[0]["key"], "ping")
                button0_state = True
        if button1.value and not button1_state:
            led.value = True
            io.send_data(send_while_idle_feeds[1]["key"], "ping")
            button1_state = True
        if button2.value and not button2_state:
            led.value = True
            io.send_data(send_while_idle_feeds[2]["key"], "ping")
            button2_state = True
    if (time.monotonic() - clock) > 15:
        #  get data
        for feed in range(3):
            try:
                data = io.receive_data(read_feeds[feed]["key"])
            except AdafruitIO_RequestError:
                print("Check that OctoPrint is sending data! Check your IO dashboard.")
            #  if a new value is detected
            if data["value"] != last_feed_msg[feed]:
                #  assign value to new_msg
                new_feed_msg[feed] = data["value"]
                msg_json[feed] = json.loads(data["value"])
                #  set servo angle
                print(read_feeds[feed]["key"])
                print()
                print(new_feed_msg[feed])
                print()
                #time.sleep(1)
                print_progress = int(msg_json[0]['progress'])
                current_file = str(msg_json[0]['path'])
                current_state = str(msg_json[1]['state_id'])
                finished_file = str(msg_json[2]['path'])
                state_value = printer_state_options.index(current_state)
                #  log msg
                last_feed_msg[feed] = new_feed_msg[feed]
            #time.sleep(1)
        if current_state == "PRINTING":
            #print_progress = int(msg_json[0]['progress'])
            progress_bar.value = print_progress
            #octoprint green
            progress_bar.bar_color = 0x13c100
            text.text = "\n".join(wrap_text_to_lines("%d%% Printed" % print_progress, 7))
            icon_grid.bitmap = printing_icons
            icon_grid.pixel_shader = printing_icons.pixel_shader
        elif current_state in ("PAUSED", "PAUSING"):
            progress_bar.value = print_progress
            progress_bar.bar_color = colors[state_value]
            text.text = "\n".join(wrap_text_to_lines("Status: %s" % current_state, 11))
            icon_grid.bitmap = printing_icons
            icon_grid.pixel_shader = printing_icons.pixel_shader
        # when a print is finished:
        elif finished_file == current_file and print_progress == 100:
            progress_bar.value = 100
            progress_bar.bar_color = purple
            text.text = "\n".join(wrap_text_to_lines("Print Finished!", 11))
            icon_grid.bitmap = finished_icon
            icon_grid.pixel_shader = finished_icon.pixel_shader
        # when printer is idle, display status
        else:
            progress_bar.value = 100
            progress_bar.bar_color = colors[state_value]
            text.text = "\n".join(wrap_text_to_lines("Status: %s" % current_state, 11))
            icon_grid.bitmap = idle_icons
            icon_grid.pixel_shader = idle_icons.pixel_shader
        #  reset clock
        clock = time.monotonic()
