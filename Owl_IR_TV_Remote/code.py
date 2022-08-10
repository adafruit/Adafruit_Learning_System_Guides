# SPDX-FileCopyrightText: 2022 Liz Clark for Adafruit Industries
# SPDX-License-Identifier: MIT

import array
import pulseio
import board
from digitalio import DigitalInOut, Direction, Pull
from adafruit_debouncer import Debouncer
import neopixel

#  button setup with Debouncer
pin = DigitalInOut(board.A2)
pin.direction = Direction.INPUT
pin.pull = Pull.UP
button = Debouncer(pin)

#  button LED
led = DigitalInOut(board.A1)
led.direction = Direction.OUTPUT

#  onboard neopixel
pix = board.NEOPIXEL
num_pixels = 1
pixel = neopixel.NeoPixel(pix, num_pixels, brightness=0.8, auto_write=False)

#  PWM setup for IR LEDs
remote = pulseio.PulseOut(board.TX, frequency=38000, duty_cycle=2**15)
#  power on pulse array
# Prevent black from reformatting the arrays.
# fmt: off
power_on = array.array('H', [9027, 4490, 577, 563, 549, 1677, 579, 1674, 582, 558,
                             554, 559, 553, 561, 551, 562, 551, 1675, 580, 1674, 572,
                             567, 555, 1672, 573, 567, 556, 558, 554, 559, 553, 560,
                             552, 562, 550, 1675, 581, 560, 552, 561, 552, 561, 551,
                             563, 549, 1677, 579, 1674, 581, 560, 552, 561, 552, 1674,
                             581, 1673, 573, 1680, 575, 1679, 577, 563, 549, 565, 547,
                             1679, 577])
#  power off pulse array
power_off = array.array('H', [9028, 4491, 576, 563, 549, 1678, 578, 1701, 554, 533,
                              579, 561, 551, 562, 551, 536, 576, 1703, 552, 1700, 556,
                              558, 554, 1698, 547, 540, 582, 558, 554, 532, 580, 560,
                              552, 561, 552, 562, 550, 563, 549, 564, 548, 565, 547,
                              566, 546, 1707, 549, 1704, 551, 562, 550, 1703, 553, 1699,
                              556, 1697, 548, 1705, 551, 1701, 554, 560, 553, 560, 552,
                              1701, 554])
# fmt: on
#  array of the pulses
signals = [power_on, power_off]
#  neopixel colors
RED = (255, 0, 0)
GREEN = (0, 255, 0)
#  array of colors
colors = [GREEN, RED]
#  index variable
s = 0

while True:
    #  scan button for update
    button.update()
    #  if the button is pressed..
    if button.fell:
        #  send the pulse
        remote.send(signals[s])
        #  update onboard neopixel
        pixel.fill(colors[s])
        pixel.show()
        #  turn on button LED
        led.value = True
        #  advance the index variable
        s = (s + 1) % 2
    #  if the button is released..
    if button.rose:
        #  turn off the button LED
        led.value = False
