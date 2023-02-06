# SPDX-FileCopyrightText: 2023 Liz Clark for Adafruit Industries
# SPDX-License-Identifier: MIT

import time
import ssl
import os
import json
import socketpool
import wifi
import adafruit_requests
from adafruit_io.adafruit_io import IO_HTTP, AdafruitIO_RequestError
import board
import digitalio
import displayio
import terminalio
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
board.DISPLAY.show(splash)

width = 165
height = 30

x = 70
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

rect = Rect(60, 0, 2, 135, fill=0xFFFFFF)
splash.append(rect)

img = displayio.OnDiskBitmap("octoprint_logo.bmp")

tile_grid = displayio.TileGrid(bitmap=img, pixel_shader=img.pixel_shader, x = 185, y=5)
splash.append(tile_grid)

text = bitmap_label.Label(terminalio.FONT, text="Connecting", scale=2, x=75, y=45)
splash.append(text)

d0_text = bitmap_label.Label(terminalio.FONT, text="Cooldown", scale=1, x=5, y=10)
splash.append(d0_text)
d1_text = bitmap_label.Label(terminalio.FONT, text="Heat up", scale=1, x=5, y=65)
splash.append(d1_text)
d2_text = bitmap_label.Label(terminalio.FONT, text="Reboot", scale=1, x=5, y=125)
splash.append(d2_text)

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

button0_state = False
button1_state = False
button2_state = False

pixel = neopixel.NeoPixel(board.NEOPIXEL, 1, brightness = 0.6)

pool = socketpool.SocketPool(wifi.radio)

requests = adafruit_requests.Session(pool, ssl.create_default_context())
io = IO_HTTP(aio_username, aio_key, requests)

try:
    # get feed
    printing_status = io.get_feed("printing")
    print_done = io.get_feed("printdone")
    printer_state = io.get_feed("printerstatechanged")
    shutdown = io.get_feed("shutdown")
    heat_up = io.get_feed("heatup")
    cooldown = io.get_feed("cooldown")
    resume = io.get_feed("printresumed")
    pause = io.get_feed("printpaused")
    cancelled = io.get_feed("printcancelled")

except AdafruitIO_RequestError:
    # if no feed exists, create one
    printing_status = io.create_new_feed("printing")
    print_done = io.create_new_feed("printdone")
    printer_state = io.create_new_feed("printerstatechanged")
    shutdown = io.create_new_feed("shutdown")
    heat_up = io.create_new_feed("heatup")
    cooldown = io.create_new_feed("cooldown")
    resume = io.create_new_feed("printresumed")
    pause = io.create_new_feed("printpaused")
    cancelled = io.create_new_feed("printcancelled")

read_feeds = [printing_status, printer_state, print_done]
send_while_idle_feeds = [cooldown, heat_up, shutdown]
send_while_printing_feeds = [pause, resume, cancelled]
new_feed_msg = ["None", "None", "None"]
last_feed_msg = ["none","none","none"]
msg_json = [{"path": "none"}, {"state_id": "NONE"}, {"path": "none"}]
print_progress = 0
current_state = 0
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
                d0_text.text = "Cooldown"
                d1_text.text = "Heat up"
                d2_text.text = "Reboot"
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
                print(read_feeds[feed]["key"])
                print()
                print(new_feed_msg[feed])
                print()
                print_progress = int(msg_json[0]['progress'])
                current_file = str(msg_json[0]['path'])
                current_state = str(msg_json[1]['state_id'])
                finished_file = str(msg_json[2]['path'])
                state_value = printer_state_options.index(current_state)
                #  log msg
                last_feed_msg[feed] = new_feed_msg[feed]
        if current_state == "PRINTING":
            progress_bar.value = print_progress
            #octoprint green
            progress_bar.bar_color = 0x13c100
            text.text = "\n".join(wrap_text_to_lines("%d%% Printed" % print_progress, 7))
            d0_text.text = "Pause"
            d1_text.text = "Resume"
            d2_text.text = "Cancel"
        elif current_state in ("PAUSED", "PAUSING"):
            progress_bar.value = print_progress
            progress_bar.bar_color = colors[state_value]
            text.text = "\n".join(wrap_text_to_lines("Status: %s" % current_state, 11))
            d0_text.text = "Pause"
            d1_text.text = "Resume"
            d2_text.text = "Cancel"
        # when a print is finished:
        elif finished_file == current_file and print_progress == 100:
            progress_bar.value = 100
            progress_bar.bar_color = purple
            text.text = "\n".join(wrap_text_to_lines("Print Finished!", 11))
            d0_text.text = "Confirm"
            d1_text.text = " "
            d2_text.text = " "
        # when printer is idle, display status
        else:
            progress_bar.value = 100
            progress_bar.bar_color = colors[state_value]
            text.text = "\n".join(wrap_text_to_lines("Status: %s" % current_state, 11))
            d0_text.text = "Cooldown"
            d1_text.text = "Heat up"
            d2_text.text = "Reboot"
        #  reset clock
        clock = time.monotonic()
