# SPDX-FileCopyrightText: 2022 Liz Clark for Adafruit Industries
# SPDX-License-Identifier: MIT

import time
import board
from digitalio import DigitalInOut, Direction, Pull
from adafruit_debouncer import Debouncer
import usb_hid
from adafruit_hid.keyboard import Keyboard
from adafruit_hid.keycode import Keycode
from adafruit_hid.mouse import Mouse
from rainbowio import colorwheel
from adafruit_seesaw.seesaw import Seesaw
from adafruit_seesaw.analoginput import AnalogInput
from adafruit_seesaw import neopixel

# LED for button
led = DigitalInOut(board.A0)
led.direction = Direction.OUTPUT

#  button setup
key_pin = DigitalInOut(board.A1)
key_pin.direction = Direction.INPUT
key_pin.pull = Pull.UP
switch = Debouncer(key_pin)

# button to toot in the game (can be any key or a mouse click)
key_pressed = Keycode.SPACE

# keyboard object
time.sleep(1)  # Sleep for a bit to avoid a race condition on some systems
keyboard = Keyboard(usb_hid.devices)

#  mouse object
mouse = Mouse(usb_hid.devices)

# NeoSlider Setup
neoslider = Seesaw(board.STEMMA_I2C(), 0x30)
pot = AnalogInput(neoslider, 18)
pixels = neopixel.NeoPixel(neoslider, 14, 4, pixel_order=neopixel.GRB)

#  scale pot value to rainbow colors
def potentiometer_to_color(value):
    return value / 1023 * 255

#  last value of the potentiometer
last_value = 0
#  difference between last_value and current value
diff = 0
#  mouse movement sensitivity
#  increase value for faster movement, decrease for slower
mouse_sensitivity = 8

while True:
	#  read the slide pot's value (range of 0 to 1023)
    y = pot.value
	#  debouncer update
    switch.update()
    # colorwheel for neoslider neopixels
    pixels.fill(colorwheel(potentiometer_to_color(pot.value)))
	#  if button released
    if switch.rose:
		#  turn off button LED
        led.value = False
		#  release all keyboard keys
        keyboard.release_all()
	#  if button pressed
    if switch.fell:
		#  turn on button LED
        led.value = True
		#  press the space bar
        keyboard.press(key_pressed)
	#  if the current value of the pot is different from the last value
    if y != last_value:
		#  if the last value was bigger
        if last_value > y:
			#  find the difference
            diff = abs(last_value - y)
			#  divide by 10
            diff = diff / 10
			#  move cursor negative for range of difference
            for i in range(diff):
                mouse.move(y=-(mouse_sensitivity))
		#  if last value was smaller
        if last_value < y:
			#  find the difference
            diff = abs(last_value - y)
			#  divide by 10
            diff = diff / 10
			#  move cursor positive for range of difference
            for i in range(diff):
                mouse.move(y=mouse_sensitivity)
		#  reset last value
        last_value = y
	#  if value is 0
    if y == 0:
		#  slight movement
        mouse.move(y=-2)
	#  if value is 1023
    if y == 1023:
		#  slight movement
        mouse.move(y=2)
