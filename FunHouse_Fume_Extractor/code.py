# SPDX-FileCopyrightText: 2021 Liz Clark for Adafruit Industries
#
# SPDX-License-Identifier: MIT

import time
import board
import simpleio
import adafruit_sgp30
import displayio
import adafruit_imageload
from adafruit_emc2101 import EMC2101
from adafruit_funhouse import FunHouse

i2c = board.I2C()  # uses board.SCL and board.SDA
# i2c = board.STEMMA_I2C()  # For using the built-in STEMMA QT connector on a microcontroller

#  setup for SGP30 sensor
sgp30 = adafruit_sgp30.Adafruit_SGP30(i2c)
#  setup for fan controller
emc = EMC2101(i2c)

print("SGP30 serial #", [hex(i) for i in sgp30.serial])

#SGP30 start-up
sgp30.iaq_init()
sgp30.set_iaq_baseline(0x8973, 0x8AAE)

#  FunHouse setup
funhouse = FunHouse(default_bg=0x0F0F00)
#  start-up bitmap
bitmap, palette = adafruit_imageload.load("/scene1_fume.bmp",
                                         bitmap=displayio.Bitmap,
                                         palette=displayio.Palette)
tile_grid = displayio.TileGrid(bitmap, pixel_shader=palette)
#  connecting bitmap
bitmap2, palette2 = adafruit_imageload.load("/scene2_fume.bmp",
                                         bitmap=displayio.Bitmap,
                                         palette=displayio.Palette)
grid2 = displayio.TileGrid(bitmap2, pixel_shader=palette2)
#  default background
bitmap3, palette3 = adafruit_imageload.load("/scene3_fume.bmp",
                                         bitmap=displayio.Bitmap,
                                         palette=displayio.Palette)
grid3 = displayio.TileGrid(bitmap3, pixel_shader=palette3)
#  internet connection icon
bitmap4, palette4 = adafruit_imageload.load("/connect_icon.bmp",
                                         bitmap=displayio.Bitmap,
                                         palette=displayio.Palette)
icon1 = displayio.TileGrid(bitmap4, pixel_shader=palette4, x = 2, y = 2)
#  red x icon
bitmap5, palette5 = adafruit_imageload.load("/x_icon.bmp",
                                         bitmap=displayio.Bitmap,
                                         palette=displayio.Palette)
icon2 = displayio.TileGrid(bitmap5, pixel_shader=palette5, x = 2, y = 2)
#  display group
group = displayio.Group()
#  adding start-up bitmap to group
group.append(tile_grid)
funhouse.splash.append(group)
#  text for fume data
fume_text = funhouse.add_text(
    text="    ",
    text_position=(110, 90),
    text_anchor_point=(0.5, 0.5),
    text_color=0xf57f20,
    text_font="fonts/Arial-Bold-24.pcf",
)
#  text for fan RPM data
fan_text = funhouse.add_text(
    text="    ",
    text_position=(110, 165),
    text_anchor_point=(0.5, 0.5),
    text_color=0x7fffff,
    text_font="fonts/Arial-Bold-24.pcf",
)
#  showing graphics
funhouse.display.show(funhouse.splash)

#  state machines
run = False #  state if main code is running
connected = False #  checks if connected to wifi
start_up = False #  state for start-up
clock = 0 #  time.monotonic() device

#  function for sending fume data to adafruit.io
def send_fume_data(solder_fumes):
    funhouse.network.push_to_io("fumes", solder_fumes)

#  function for sending fan rpm to adafruit.io
def send_fan_data(fan_rpm):
    funhouse.network.push_to_io("fan-speed", fan_rpm)

while True:
    #  if main program has not started
    if not run:
        #  if you press the down button
        if funhouse.peripherals.button_down:
            print("run")
            #  remove start-up bitmap
            group.remove(tile_grid)
            #  add main bitmap
            group.append(grid3)
            #  add red x icon to show not connected to internet
            group.append(icon2)
            #  change state for main program
            run = True
        #  if you press the middle button
        if funhouse.peripherals.button_sel:
            #  remove start-up bitmap
            group.remove(tile_grid)
            #  add connecting... bitmap
            group.append(grid2)
            #  connect to the network
            funhouse.network.connect()
            print("connecting")
            #  change state for network
            connected = True
            #  start main program
            start_up = True
            #  start time.monotonic()
            clock = time.monotonic()
        #  after connecting to the internet
        if start_up:
            #  remove connecting bitmap
            group.remove(grid2)
            #  add main bitmap
            group.append(grid3)
            #  add internet icon
            group.append(icon1)
            #  start main program
            run = True
            #  reset start-up state
            start_up = False

    #  run state for main program after selecting whether or not to connect to wifi
    if run:
        #  print eCO2 and TVOC data to REPL
        print("eCO2 = %d ppm \t TVOC = %d ppb" % (sgp30.eCO2, sgp30.TVOC))
        #  2 second delay
        time.sleep(2)

        #  fumes variable for reading from SGP30
        #  comment out either TVOC or eCO2 depending on data preference
        fumes = sgp30.TVOC
        #  fumes = sgp30.eCO2

        #  mapping fumes data to fan RPM
        #  value for TVOC
        mapped_val = simpleio.map_range(fumes, 10, 1000, 10, 100)
        #  value for eCO2
        #  mapped_val = simpleio.map_range(fumes, 400, 2500, 10, 100)

        #  adding fume text
        #  PPB is for TVOC, PPM is for eCO2
        funhouse.set_text("%d PPB" % fumes, fume_text)
        #  funhouse.set_text("%d PPM" % fumes, fume_text)

        #  adding fan's RPM text
        funhouse.set_text("%d%s" % (mapped_val, "%"), fan_text)
        #  printing fan's data to the REPL
        print("fan = ", mapped_val)
        #  setting fan's RPM
        emc.manual_fan_speed = int(mapped_val)

        #  if you're connected to wifi and 15 seconds has passed
        if connected and ((clock + 15) < time.monotonic()):
            #  send fume data to adafruit.io
            send_fume_data(fumes)
            #  send fan RPM to adafruit.io
            send_fan_data(mapped_val)
            #  REPL printout
            print("data sent")
            #  reset clock
            clock = time.monotonic()
        #  if you're connected to wifi and you press the up button
        if connected and funhouse.peripherals.button_up:
            #  the internet icon is removed
            group.remove(icon1)
            #  the red x icon is added
            group.append(icon2)
            #  reset connected state - no longer sending data to adafruit.io
            connected = False
            #  REPL printout
            print("disconnected")
            #  1 second delay
            time.sleep(1)
        #  if you're NOT connected to wifi and you press the up button
        if not connected and funhouse.peripherals.button_up:
            #  the red x icon is removed
            group.remove(icon2)
            #  the internet icon is added
            group.append(icon1)
            #  the connection state is true - start sending data to adafruit.io
            connected = True
            #  REPL printout
            print("connected")
            #  1 second delay
            time.sleep(1)
