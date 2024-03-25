# SPDX-FileCopyrightText: 2024 Liz Clark for Adafruit Industries
#
# SPDX-License-Identifier: MIT

import time
import os
import ssl
import wifi
import socketpool
import board
import digitalio
import displayio
import adafruit_requests
from adafruit_bitmap_font import bitmap_font
from adafruit_display_shapes.circle import Circle
from adafruit_display_text import bitmap_label
from adafruit_seesaw import seesaw, rotaryio, digitalio as seesaw_digitalio, neopixel
from adafruit_ticks import ticks_ms, ticks_add, ticks_diff

num_lights = 1
light = os.getenv('ELGATO_LIGHT')
clock_clock = ticks_ms()
clock_timer = 3 * 1000

i2c = board.I2C()  # uses board.SCL and board.SDA
seesaw = seesaw.Seesaw(i2c, addr=0x36)
encoder = rotaryio.IncrementalEncoder(seesaw)
seesaw.pin_mode(24, seesaw.INPUT_PULLUP)
switch = seesaw_digitalio.DigitalIO(seesaw, 24)
switch_state = False
pixel = neopixel.NeoPixel(seesaw, 6, 1)
pixel.brightness = 0.2
pixel.fill((255, 0, 0))
print()
print("Connecting to WiFi")
#  connect to your SSID
try:
    wifi.radio.connect(os.getenv('CIRCUITPY_WIFI_SSID'), os.getenv('CIRCUITPY_WIFI_PASSWORD'))
# pylint: disable = broad-exception-caught
except Exception:
    wifi.radio.connect(os.getenv('WIFI_SSID'), os.getenv('WIFI_PASSWORD'))
print("Connected to WiFi")
pixel.fill((0, 0, 255))

pool = socketpool.SocketPool(wifi.radio)
requests = adafruit_requests.Session(pool, ssl.create_default_context())

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

group = displayio.Group()
board.DISPLAY.root_group = group

# font for graphics
sm_file = "/roundedHeavy-26.bdf"
sm_font = bitmap_font.load_font(sm_file)
# font for text only
lg_file = "/roundedHeavy-46.bdf"
lg_font = bitmap_font.load_font(lg_file)
http_text = bitmap_label.Label(sm_font, text=" ")
http_text.anchor_point = (1.0, 0.0)
http_text.anchored_position = (board.DISPLAY.width, 0)
group.append(http_text)
status_text = bitmap_label.Label(sm_font, text=" ")
status_text.anchor_point = (0.0, 0.5)
status_text.anchored_position = (0, board.DISPLAY.height / 2)
group.append(status_text)
temp_text = bitmap_label.Label(lg_font, text=" K")
temp_text.anchor_point = (1.0, 0.5)
temp_text.anchored_position = (board.DISPLAY.width, board.DISPLAY.height / 2)
group.append(temp_text)
bright_text = bitmap_label.Label(lg_font, text=" %", x=board.DISPLAY.width//2, y=90)
bright_text.anchor_point = (1.0, 1.0)
bright_text.anchored_position = (board.DISPLAY.width, board.DISPLAY.height - 15)
group.append(bright_text)
onOff_circ = Circle(12, 12, 10, fill=None, stroke = 2, outline = 0xcccc00)
group.append(onOff_circ)

def kelvin_to_elgato(value):
    t = value * 0.05
    t = max(min(344, int(t)), 143)
    return t

def elgato_to_kelvin(value):
    t = value / 0.05
    return t

def ctrl_light(b, t, onOff):
    url = f"http://{light}:9123/elgato/lights"
    json = {"numberOfLights":num_lights,"lights":[{"on":onOff,"brightness":b,"temperature":t}]}
    print(f"PUTting data to {url}: {json}")
    status_text.text = "sending.."
    for i in range(5):
        try:
            pixel.fill((0, 255, 0))
            r = requests.request(method="PUT", url=url, data=None, json=json,
                                 headers = {'Content-Type': 'application/json'}, timeout=10)
            print("-" * 40)
            print(r.status_code)
            # if PUT fails, try again
            if r.status_code != 200:
                status_text.text = "..sending.."
                pixel.fill((255, 255, 0))
                time.sleep(2)
                r = requests.request(method="PUT", url=url, data=None, json=json,
                                     headers = {'Content-Type': 'application/json'}, timeout=10)
            if r.status_code != 200:
                pixel.fill((255, 0, 0))
        except Exception:
            pixel.fill((255, 0, 0))
            time.sleep(2)
            if i < 5 - 1:
                continue
            raise
        break
    status_text.text = "sent!"
    light_indicator(onOff)
    pixel.fill((255, 0, 255))

def read_light():
    status_text.text = "reading.."
    for i in range(5):
        try:
            pixel.fill((0, 255, 0))
            r = requests.get(f"http://{light}:9123/elgato/lights")
            j = r.json()
            if r.status_code != 200:
                status_text.text = "..reading.."
                pixel.fill((255, 255, 0))
                time.sleep(2)
                r = requests.get(f"http://{light}:9123/elgato/lights")
                j = r.json()
            if r.status_code != 200:
                pixel.fill((255, 0, 0))
        except Exception:
            pixel.fill((255, 0, 0))
            time.sleep(2)
            if i < 5 - 1:
                continue
            raise
        break
    status_text.text = "read!"
    pixel.fill((255, 0, 255))
    onOff = j['lights'][0]['on']
    light_indicator(onOff)
    b = round(j['lights'][0]['brightness'] / 10) * 10
    bright_text.text = f"{b}%"
    t = j['lights'][0]['temperature']
    color_t = round(elgato_to_kelvin(t) / 100) * 100
    temp_text.text = f"{color_t}K"
    return b, color_t, t, onOff

def light_indicator(onOff):
    if onOff:
        onOff_circ.fill = 0xcccc00
    else:
        onOff_circ.fill = None

selected_light = 0
adjust_temp = True
last_position = 0

http_text.text = f"{light}"
# get on/off state of light on start-up
try:
    brightness, color_temp, temp, light_on = read_light()
except Exception:
    print()
    print("Could not find your Elgato light on the network..")
    print("Make sure it is powered on and that its IP address is correct in settings.toml.")
    print()
    raise

while True:
    position = encoder.position
    # reset button state on release
    if not switch.value and switch_state:
        switch_state = False
    if button0.value and button0_state:
        button0_state = False
    if not button1.value and button1_state:
        button1_state = False
    if not button2.value and button2_state:
        button2_state = False

    if position != last_position:
        if position > last_position:
            if adjust_temp:
                color_temp = color_temp + 100
                color_temp = max(min(7000, color_temp), 2900)
                temp_text.text = f"{color_temp}K"
            else:
                brightness = brightness + 10
                brightness = max(min(100, brightness), 10)
                bright_text.text = f"{brightness}%"
        else:
            if adjust_temp:
                color_temp = color_temp - 100
                color_temp = max(min(7000, color_temp), 2900)
                temp_text.text = f"{color_temp}K"
            else:
                brightness = brightness - 10
                brightness = max(min(100, brightness), 10)
                bright_text.text = f"{brightness}%"
        temp = kelvin_to_elgato(color_temp)
        last_position = position
    # switch between adjusting color temp or brightness
    if switch.value and not switch_state:
        switch_state = True
        adjust_temp = not adjust_temp
    # toggle light on/off
    if not button0.value and not button0_state:
        button0_state = True
        light_on = not light_on
        ctrl_light(brightness, temp, light_on)
        clock_clock = ticks_add(clock_clock, clock_timer)
    # update brightness/temp
    if button1.value and not button1_state:
        button1_state = True
        light_on = True
        ctrl_light(brightness, temp, light_on)
        clock_clock = ticks_add(clock_clock, clock_timer)
    # check values
    if button2.value and not button2_state:
        button2_state = True
        brightness, color_temp, temp, light_on = read_light()
        clock_clock = ticks_add(clock_clock, clock_timer)
    if ticks_diff(ticks_ms(), clock_clock) >= clock_timer:
        status_text.text = "Connected"
        clock_clock = ticks_add(clock_clock, clock_timer)
