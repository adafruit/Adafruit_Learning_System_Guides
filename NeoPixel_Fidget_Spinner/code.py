# SPDX-FileCopyrightText: 2023 Liz Clark for Adafruit Industries
# SPDX-License-Identifier: MIT

import time
import random
import board
import neopixel
from adafruit_seesaw import seesaw, rotaryio, digitalio
from adafruit_debouncer import Button
from rainbowio import colorwheel
from adafruit_led_animation import color

# NeoPixel ring setup. Update num_pixels if using a different ring.
num_pixels = 24
pixels = neopixel.NeoPixel(board.D5, num_pixels, auto_write=False)

i2c = board.STEMMA_I2C()
seesaw = seesaw.Seesaw(i2c, addr=0x49)

buttons = []
for b in range(1, 6):
    seesaw.pin_mode(b, seesaw.INPUT_PULLUP)
    ss_pin = digitalio.DigitalIO(seesaw, b)
    button = Button(ss_pin, long_duration_ms=1000)
    buttons.append(button)

encoder = rotaryio.IncrementalEncoder(seesaw)
last_position = 0

button_names = ["Select", "Up", "Left", "Down", "Right"]
colors = [color.RED, color.YELLOW, color.ORANGE, color.GREEN,
          color.TEAL, color.CYAN, color.BLUE, color.PURPLE, color.MAGENTA]

# rainbow cycle function
def rainbow_cycle(wait):
    for j in range(255):
        for i in range(num_pixels):
            rc_index = (i * 256 // num_pixels) + j
            pixels[i] = colorwheel(rc_index & 255)
        pixels.show()
        time.sleep(wait)

color_index = 0
game_mode = False
pixel = 0
num = 0
last_num = 0
now_color = 0
next_color = 1
speed = 0.1
level = 0.005
final_level = 0.001
new_target = True

while True:
    if not game_mode:
        for b in range(5):
            buttons[b].update()
            if buttons[b].released or buttons[b].pressed:
                pixels.fill(color.BLACK)
        position = encoder.position
        if position != last_position:
            pixels[last_position % num_pixels] = color.BLACK
            pixels[position % num_pixels] = colors[color_index]
            # print("Position: {}".format(position))
            last_position = position

        if buttons[0].pressed:
            # print("Center button!")
            pixels.fill(colors[color_index])

        elif buttons[0].long_press:
            # print("long press detected")
            pixels.fill(color.BLACK)
            new_target = True
            game_mode = True

        if buttons[1].pressed:
            # print("Up button!")
            color_index = (color_index + 1) % len(colors)
            pixels[10] = colors[color_index]

        if buttons[2].pressed:
            # print("Left button!")
            color_index = (color_index + 1) % len(colors)
            pixels[4] = colors[color_index]

        if buttons[3].pressed:
            # print("Down button!")
            color_index = (color_index - 1) % len(colors)
            pixels[22] = colors[color_index]

        if buttons[4].pressed:
            # print("Right button!")
            color_index = (color_index - 1) % len(colors)
            pixels[16] = colors[color_index]

        pixels.show()
    if game_mode:
        buttons[0].update()
        if buttons[0].long_press:
            # print("long press detected")
            pixels.fill(color.BLACK)
            pixels.show()
            game_mode = False
            pixels.fill(colors[color_index])
        #  if new level starting..
        if new_target:
            if buttons[0].released:
            #  randomize target location
                y = random.randint(5, 22)
                x = y - 1
                z = y + 1
                new_target = False
                pixels[x] = color.WHITE
                pixels[y] = colors[next_color]
                pixels[z] = color.WHITE
        else:
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
                    num += 1
                #  send chaser back to the beginning of the circle
                if num == num_pixels:
                    last_num = num - 1
                    pixels[last_num] = color.BLACK
                    pixels.show()
                    num = 0
                #  if the chaser hits the target...
                if last_num in [x, y, z] and not buttons[0].value:
                    #  fills with the next color
                    pixels.fill(colors[next_color])
                    pixels.show()
                    #  chaser resets
                    num = 0
                    time.sleep(0.5)
                    pixels.fill(color.BLACK)
                    pixels.show()
                    #  speed increases for next level
                    speed = speed - level
                    #  color updates
                    next_color = (next_color + 1) % 9
                    now_color = (now_color + 1) % 9
                    #  setup for new target
                    new_target = True
                #  if the chaser misses the target...
                if last_num not in [x, y, z] and not buttons[0].value:
                    #  fills with current chaser color
                    pixels.fill(color.BLACK)
                    pixels.show()
                    #  chaser is reset
                    num = 0
                    #  speed is reset to default
                    speed = 0.1
                    #  colors are reset
                    next_color = 1
                    now_color = 0
                    #  setup for new target
                    new_target = True
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
