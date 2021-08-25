# 'Cyber falls' sketch
# Creates a fiery rain-like effect on multiple NeoPixel strips.
# Requires Adafruit Trinket and NeoPixel strips.  Strip length is
# inherently limited by Trinket RAM and processing power; this is
# written for five 15-pixel strands, which are paired up per pin
# for ten 15-pixel strips total.

import time
import board
import neopixel
import adafruit_fancyled.adafruit_fancyled as fancy

num_leds = 15       # number of LEDs per strip
saturation = 255    # 0-255, 0 is pure white, 255 is fully saturated color
blend = True        # color blending between palette indices
brightness = 0.5    # half brightness the range is 0.0 - 1.0
concurrent = 3      # number of LEDs on at a time
on_time = 0.04      # 0.04 seconds == 40 milliseconds

# NeoPixel objects using all five Trinket M0 GPIO pins 0-4
drop0 = neopixel.NeoPixel(board.D0, num_leds)
drop1 = neopixel.NeoPixel(board.D1, num_leds)
drop2 = neopixel.NeoPixel(board.D2, num_leds)
drop3 = neopixel.NeoPixel(board.D3, num_leds)
drop4 = neopixel.NeoPixel(board.D4, num_leds)

# list of neopixel strips
drop_list = [drop0, drop1, drop2, drop3, drop4]

def led_drops(strip):

    # FancyLED allows for mixing colors with palettes
    palette = [fancy.CRGB(200, 255, 200),       # lighter (more white) green
               fancy.CRGB(0, 255, 0)]           # full green

    for i in range(num_leds):
        # FancyLED can handle the gamma adjustment, brightness and RGB settings
        color = fancy.palette_lookup(palette, i / num_leds)
        color = fancy.gamma_adjust(color, brightness=brightness)
        strip[i] = color.pack()

        # turn off the LEDs as we go for raindrop effect
        if  i >= concurrent:
            strip[i - concurrent] = (0,0,0)

        if i >= num_leds - 1:
            for j in range(concurrent,-1,-1):
                strip[i-j] = (0,0,0)
                time.sleep(on_time)

        time.sleep(on_time)

while True:

    # loop through each neopixel strip in our list
    for drops in drop_list:
        led_drops(drops)
