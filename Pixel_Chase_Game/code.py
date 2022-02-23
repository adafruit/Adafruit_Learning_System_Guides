# SPDX-FileCopyrightText: 2020 Liz Clark for Adafruit Industries
#
# SPDX-License-Identifier: MIT

import time
import random
import board
from rainbowio import colorwheel
import neopixel
import digitalio
import adafruit_led_animation.color as color

#  button pin setup
button = digitalio.DigitalInOut(board.D5)
button.direction = digitalio.Direction.INPUT
button.pull = digitalio.Pull.UP

#  neopixel setup
pixel_pin = board.D6
num_pixels = 61

pixels = neopixel.NeoPixel(pixel_pin, num_pixels, brightness=0.2, auto_write=False)

def rainbow_cycle(wait):
    for j in range(255):
        for i in range(num_pixels):
            rc_index = (i * 256 // 10) + j
            pixels[i] = colorwheel(rc_index & 255)
        pixels.show()
        time.sleep(wait)

#  color_chase setup
def color_chase(c, wait):
    for i in range(num_pixels):
        pixels[i] = c
        time.sleep(wait)
        pixels.show()
    time.sleep(0.5)

#  function to blink the neopixels when you lose
def game_over():
    color_chase(color.BLACK, 0.05)
    pixels.fill(color.RED)
    pixels.show()
    time.sleep(0.5)
    pixels.fill(color.BLACK)
    pixels.show()
    time.sleep(0.5)
    pixels.fill(color.RED)
    pixels.show()
    time.sleep(0.5)
    pixels.fill(color.BLACK)
    pixels.show()
    time.sleep(0.5)
    pixels.fill(color.RED)
    pixels.show()
    time.sleep(1)

#  variables and states
pixel = 0
num = 0
last_num = 0
now_color = 0
next_color = 1
speed = 0.1
level = 0.005
final_level = 0.001
new_target = True
button_state = False

#  neopixel colors
colors = [color.RED, color.ORANGE, color.YELLOW, color.GREEN, color.TEAL, color.CYAN,
          color.BLUE, color.PURPLE, color.MAGENTA, color.GOLD, color.AQUA, color.PINK]

while True:

    #  button debouncing
    if not button.value and not button_state:
        button_state = True

    #  if new level starting..
    if new_target:
        #  randomize target location
        y = int(random.randint(5, 55))
        x = int(y - 1)
        z = int(y + 1)
        new_target = False
        print(x, y, z)
    pixels[x] = color.WHITE
    pixels[y] = colors[next_color]
    pixels[z] = color.WHITE
    #  delay without time.sleep()
    if (pixel + speed) < time.monotonic():
        #  turn off pixel behind chaser
        if num > 0:
            last_num = num - 1
            pixels[last_num] = color.BLACK
            pixels.show()
        #  keep target pixels their colors when the chaser passes
        if last_num in (x, y, z):
            pixels[x] = color.WHITE
            pixels[y] = colors[next_color]
            pixels[z] = color.WHITE
        #  move chaser pixel by one
        if num < num_pixels:
            pixels[num] = colors[now_color]
            pixels.show()
            #print(num)
            #print("target is", y)
            num += 1
        #  send chaser back to the beginning of the circle
        if num == num_pixels:
            last_num = num - 1
            pixels[last_num] = color.BLACK
            pixels.show()
            num = 0
        #  if the chaser hits the target...
        if last_num in [x, y, z] and not button.value:
            button_state = False
            #  fills with the next color
            pixels.fill(colors[next_color])
            pixels.show()
            print(num)
            print(x, y, z)
            #  chaser resets
            num = 0
            time.sleep(0.5)
            pixels.fill(color.BLACK)
            pixels.show()
            #  speed increases for next level
            speed = speed - level
            #  color updates
            next_color = next_color + 1
            if next_color > 11:
                next_color = 0
            now_color = now_color + 1
            if now_color > 11:
                now_color = 0
            #  setup for new target
            new_target = True
            print("speed is", speed)
            print("button is", button.value)
        #  if the chaser misses the target...
        if last_num not in [x, y, z] and not button.value:
            button_state = False
            print(num)
            print(x, y, z)
            #  fills with current chaser color
            pixels.fill(colors[now_color])
            pixels.show()
            #  function to flash all pixels red
            game_over()
            #  chaser is reset
            num = 0
            pixels.fill(color.BLACK)
            pixels.show()
            #  speed is reset to default
            speed = 0.1
            #  colors are reset
            next_color = 1
            now_color = 0
            #  setup for new target
            new_target = True
            print("speed is", speed)
            print("button is", button.value)
        #  when you have beaten all the levels...
        if speed < final_level:
            #  rainbows!
            rainbow_cycle(0.01)
            time.sleep(1)
            #  chaser is reset
            num = 0
            pixels.fill(color.BLACK)
            pixels.show()
            #  speed is reset to default
            speed = 0.1
            #  colors are reset
            next_color = 1
            now_color = 0
            #  setup for new target
            new_target = True
        #  time.monotonic() is reset for the delay
        pixel = time.monotonic()
