# SPDX-FileCopyrightText: 2022 Liz Clark for Adafruit Industries
#
# SPDX-License-Identifier: MIT

import os
import time
import ipaddress
import wifi
import socketpool
import busio
import board
import microcontroller
import displayio
import terminalio
from adafruit_display_text import label
import adafruit_displayio_ssd1306
import adafruit_imageload
from digitalio import DigitalInOut, Direction
from adafruit_httpserver.server import HTTPServer
from adafruit_httpserver.request import HTTPRequest
from adafruit_httpserver.response import HTTPResponse
from adafruit_httpserver.methods import HTTPMethod
from adafruit_httpserver.mime_type import MIMEType
from adafruit_onewire.bus import OneWireBus
from adafruit_ds18x20 import DS18X20

#  onboard LED setup
led = DigitalInOut(board.LED)
led.direction = Direction.OUTPUT
led.value = False

#  pin used for party parrot animation
parrot_pin = DigitalInOut(board.GP10)
parrot_pin.direction = Direction.OUTPUT
parrot_pin.value = False

# one-wire bus for DS18B20
ow_bus = OneWireBus(board.GP6)

# scan for temp sensor
ds18 = DS18X20(ow_bus, ow_bus.scan()[0])

#  function to convert celcius to fahrenheit
def c_to_f(temp):
    temp_f = (temp * 9/5) + 32
    return temp_f

#  i2c display setup
displayio.release_displays()
oled_reset = board.GP9

# STEMMA I2C on picowbell
i2c = busio.I2C(board.GP5, board.GP4)
display_bus = displayio.I2CDisplay(i2c, device_address=0x3D, reset=oled_reset)

WIDTH = 128
HEIGHT = 64
offset_y = 5

display = adafruit_displayio_ssd1306.SSD1306(display_bus, width=WIDTH, height=HEIGHT)

# default display group
splash = displayio.Group()
display.show(splash)

#  connect to network
print()
print("Connecting to WiFi")
connect_text = "Connecting..."
connect_text_area = label.Label(
    terminalio.FONT, text=connect_text, color=0xFFFFFF, x=0, y=offset_y
)
splash.append(connect_text_area)

#  set static IP address
ipv4 =  ipaddress.IPv4Address("192.168.1.42")
netmask =  ipaddress.IPv4Address("255.255.255.0")
gateway =  ipaddress.IPv4Address("192.168.1.1")
wifi.radio.set_ipv4_address(ipv4=ipv4,netmask=netmask,gateway=gateway)
#  connect to your SSID
wifi.radio.connect(os.getenv('CIRCUITPY_WIFI_SSID'), os.getenv('CIRCUITPY_WIFI_PASSWORD'))

print("Connected to WiFi")
pool = socketpool.SocketPool(wifi.radio)
server = HTTPServer(pool, "/static")

#  variables for HTML
#  comment/uncomment desired temp unit

#  temp_test = str(ds18.temperature)
#  unit = "C"
temp_test = str(c_to_f(ds18.temperature))
unit = "F"
#  font for HTML
font_family = "monospace"

#  the HTML script
#  setup as an f string
#  this way, can insert string variables from code.py directly
#  of note, use {{ and }} if something from html *actually* needs to be in brackets
#  i.e. CSS style formatting
def webpage():
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
    <meta http-equiv="Content-type" content="text/html;charset=utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
    html{{font-family: {font_family}; background-color: lightgrey;
    display:inline-block; margin: 0px auto; text-align: center;}}
      h1{{color: deeppink; width: 200; word-wrap: break-word; padding: 2vh; font-size: 35px;}}
      p{{font-size: 1.5rem; width: 200; word-wrap: break-word;}}
      .button{{font-family: {font_family};display: inline-block;
      background-color: black; border: none;
      border-radius: 4px; color: white; padding: 16px 40px;
      text-decoration: none; font-size: 30px; margin: 2px; cursor: pointer;}}
      p.dotted {{margin: auto;
      width: 75%; font-size: 25px; text-align: center;}}
    </style>
    </head>
    <body>
    <title>Pico W HTTP Server</title>
    <h1>Pico W HTTP Server</h1>
    <br>
    <p class="dotted">This is a Pico W running an HTTP server with CircuitPython.</p>
    <br>
    <p class="dotted">The current ambient temperature near the Pico W is
    <span style="color: deeppink;">{temp_test}°{unit}</span></p><br>
    <h1>Control the LED on the Pico W with these buttons:</h1><br>
    <form accept-charset="utf-8" method="POST">
    <button class="button" name="LED ON" value="ON" type="submit">LED ON</button></a></p></form>
    <p><form accept-charset="utf-8" method="POST">
    <button class="button" name="LED OFF" value="OFF" type="submit">LED OFF</button></a></p></form>
    <h1>Party?</h>
    <p><form accept-charset="utf-8" method="POST">
    <button class="button" name="party" value="party" type="submit">PARTY!</button></a></p></form>
    </body></html>
    """
    return html

#  route default static IP
@server.route("/")
def base(request: HTTPRequest):  # pylint: disable=unused-argument
    #  serve the HTML f string
    #  with content type text/html
    with HTTPResponse(request, content_type=MIMEType.TYPE_HTML) as response:
        response.send(f"{webpage()}")

#  if a button is pressed on the site
@server.route("/", method=HTTPMethod.POST)
def buttonpress(request: HTTPRequest):
    #  get the raw text
    raw_text = request.raw_request.decode("utf8")
    print(raw_text)
    #  if the led on button was pressed
    if "ON" in raw_text:
        #  turn on the onboard LED
        led.value = True
    #  if the led off button was pressed
    if "OFF" in raw_text:
        #  turn the onboard LED off
        led.value = False
    #  if the party button was pressed
    if "party" in raw_text:
        #  toggle the parrot_pin value
        parrot_pin.value = not parrot_pin.value
    #  reload site
    with HTTPResponse(request, content_type=MIMEType.TYPE_HTML) as response:
        response.send(f"{webpage()}")

print("starting server..")
# startup the server
try:
    server.start(str(wifi.radio.ipv4_address))
    print("Listening on http://%s:80" % wifi.radio.ipv4_address)
#  if the server fails to begin, restart the pico w
except OSError:
    time.sleep(5)
    print("restarting..")
    microcontroller.reset()
ping_address = ipaddress.ip_address("8.8.4.4")

#  text objects for screen
#  connected to SSID text
connect_text_area.text = "Connected to:"
ssid_text = "%s" % os.getenv('WIFI_SSID')
ssid_text_area = label.Label(
    terminalio.FONT, text=ssid_text, color=0xFFFFFF, x=0, y=offset_y+15
)
splash.append(ssid_text_area)
#  display ip address
ip_text = "IP: %s" % wifi.radio.ipv4_address
ip_text_area = label.Label(
    terminalio.FONT, text=ip_text, color=0xFFFFFF, x=0, y=offset_y+30
)
splash.append(ip_text_area)
#  display temp reading
temp_text = "Temperature: %.02f F" % float(temp_test)
temp_text_area = label.Label(
    terminalio.FONT, text=temp_text, color=0xFFFFFF, x=0, y=offset_y+45
)
splash.append(temp_text_area)

#  party parrot display group
parrot_group = displayio.Group()
#  load in party parrot bitmap
parrot_bit, parrot_pal = adafruit_imageload.load("/partyParrots64.bmp",
                                                 bitmap=displayio.Bitmap,
                                                 palette=displayio.Palette)
parrot_grid = displayio.TileGrid(parrot_bit, pixel_shader=parrot_pal,
                                 width=1, height=1,
                                 tile_height=64, tile_width=64,
                                 default_tile=1,
                                 x=32, y=0)
parrot_group.append(parrot_grid)

clock = time.monotonic() #  time.monotonic() holder for server ping
parrot = False #  parrot state
party = 0 #  time.monotonic() holder for party parrot
p = 0 #  index for tilegrid

while True:
    try:
        #  every 30 seconds, ping server & update temp reading
        if (clock + 30) < time.monotonic():
            if wifi.radio.ping(ping_address) is None:
                connect_text_area.text = "Disconnected!"
                ssid_text_area.text = None
                print("lost connection")
            else:
                connect_text_area.text = "Connected to:"
                ssid_text_area.text = "%s" % os.getenv('WIFI_SSID')
                print("connected")
            clock = time.monotonic()
            #  comment/uncomment for desired units
            #  temp_test = str(ds18.temperature)
            temp_test = str(c_to_f(ds18.temperature))
            temp_text_area.text = "Temperature: %s F" % temp_test

        #if parrot is True:
        if parrot_pin.value is True:
            #  switch to party parrot display group
            display.show(parrot_group)
            if (party + 0.1) < time.monotonic():
                #  the party parrot animation cycles
                parrot_grid[0] = p
                #  p is the tilegrid index location
                p = (p + 1) % 10
                party = time.monotonic()
        #  if it isn't a party
        else:
            #  show default display with info
            display.show(splash)
        #  poll the server for incoming/outgoing requests
        server.poll()
    # pylint: disable=broad-except
    except Exception as e:
        print(e)
        continue
