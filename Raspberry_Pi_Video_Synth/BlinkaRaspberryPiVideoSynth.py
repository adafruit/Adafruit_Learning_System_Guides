# SPDX-FileCopyrightText: 2022 Liz Clark for Adafruit Industries
#
# SPDX-License-Identifier: MIT

import socket
import time
import board
import simpleio
import adafruit_vl53l4cd
from adafruit_seesaw import seesaw, rotaryio, neopixel
from adafruit_seesaw.analoginput import AnalogInput

#  VL53L4CD setup
i2c = board.I2C()  # uses board.SCL and board.SDA
# i2c = board.STEMMA_I2C()  # For using the built-in STEMMA QT connector on a microcontroller
vl53 = adafruit_vl53l4cd.VL53L4CD(i2c)

# rotary encoder setup
encoder = seesaw.Seesaw(i2c, addr=0x36)
encoder.pin_mode(24, encoder.INPUT_PULLUP)
rot_encoder = rotaryio.IncrementalEncoder(encoder)

#  neoslider setup - analog slide pot and neopixel
# 0x30 = red control
# 0x31 = green control
# 0x32 = blue control
red_slider = seesaw.Seesaw(i2c, 0x30)
red_pot = AnalogInput(red_slider, 18)
r_pix = neopixel.NeoPixel(red_slider, 14, 4)

g_slider = seesaw.Seesaw(i2c, 0x31)
green_pot = AnalogInput(g_slider, 18)
g_pix = neopixel.NeoPixel(g_slider, 14, 4)

b_slider = seesaw.Seesaw(i2c, 0x32)
blue_pot = AnalogInput(b_slider, 18)
b_pix = neopixel.NeoPixel(b_slider, 14, 4)

#  rotary encoder position tracker
last_position = 0

#  neoslider position trackers
last_r = 0
last_g = 0
last_b = 0

#  VL53L4CD value tracker
last_flight = 0

#  rotary encoder index
x = 0

#  VL53L4CD start-up
vl53.inter_measurement = 0
vl53.timing_budget = 200

vl53.start_ranging()

#  HTTP socket setup
s = socket.socket()
print("socket check")

port = 12345

s.bind(('', port))
print("socket binded to %s" %(port))

s.listen(1)
print("listening")

time.sleep(10)

c, addr = s.accept()
print('got connected', addr)

while True:
    #  reset the VL53L4CD
    vl53.clear_interrupt()

    #  rotary encoder position read
    position = -rot_encoder.position

    #  VL53L4CD distance read
    flight = vl53.distance

    #  mapping neosliders to use 0-255 range for RGB values in Processing
    r_mapped = simpleio.map_range(red_pot.value, 0, 1023, 0, 255)
    g_mapped = simpleio.map_range(green_pot.value, 0, 1023, 0, 255)
    b_mapped = simpleio.map_range(blue_pot.value, 0, 1023, 0, 255)

    #  converting neoslider data to integers
    r_pot = int(r_mapped)
    g_pot = int(g_mapped)
    b_pot = int(b_mapped)

    #  set neopixels on neosliders to match background color of Processing animations
    r_pix.fill((r_pot, g_pot, b_pot))
    g_pix.fill((r_pot, g_pot, b_pot))
    b_pix.fill((r_pot, g_pot, b_pot))

    #  rotary encoder position check
    if position != last_position:
        #  rotary encoder is ranged to 0-3
        if position > last_position:
            x = (x + 1) % 4
        if position < last_position:
            x = (x - 1) % 4
        #  send rotary encoder value over socket
        #  identifying string is "enc"
        c.send(str.encode(' '.join(["enc", str(x)])))
        #  reset last_position
        last_position = position
    #  sliders only update data for changes >15 to avoid flooding socket
    #  red neoslider position check
    if abs(r_pot - last_r) > 2:
        #  send red neoslider data over socket
        #  identifying string is "red"
        c.send(str.encode(' '.join(["red", str(r_pot)])))
        #  reset last_r
        last_r = r_pot
    #  green neoslider position check
    if abs(g_pot - last_g) > 2:
        #  send green neoslider data over socket
        #  identifying string is "green"
        c.send(str.encode(' '.join(["green", str(g_pot)])))
        #  reset last_g
        last_g = g_pot
    #  blue neoslider position check
    if abs(b_pot - last_b) > 2:
        #  send blue neoslider data over socket
        #  identifying string is "blue"
        c.send(str.encode(' '.join(["blue", str(b_pot)])))
        #  reset last_b
        last_b = b_pot
    #  VL53L4CD value check

    #  setting max value of 45
    if flight > 45:
        flight = 45
        last_flight = flight
    if abs(flight - last_flight) > 2:
        print(flight)
        #  send VL53L4CD data over socket
        #  identifying string is "flight"
        c.send(str.encode(' '.join(["flight", str(flight)])))
            #  reset last_flight
        last_flight = flight
    
