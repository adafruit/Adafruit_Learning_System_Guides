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

num_leds = 16       # number of LEDs per strip
saturation = 255    # 0-255, 0 is pure white, 255 is fully saturated color
blend = True        # color blending between palette indices
brightness = 0.8    # brightness the range is 0.0 - 1.0
concurrent = 16     # number of LEDs on at a time
on_time = 0.04      # 0.04 seconds == 40 milliseconds

# NeoPixel objects using 
drop0 = neopixel.NeoPixel(board.D0, num_leds)

def led_drops(strip):

    # FancyLED allows for mixing colors with palettes
    palette = [fancy.CRGB(200, 255, 200),       # lighter (more white) green
               fancy.CRGB(0, 255, 0)]           # full green

    # heat colors
    palette = [0x330000, 0x660000, 0x990000, 0xCC0000, 0xFF0000,
               0xFF3300, 0xFF6600, 0xFF9900, 0xFFCC00, 0xFFFF00,
               0xFFFF33, 0xFFFF66, 0xFFFF99, 0xFFFFCC]


    for i in range(num_leds):
        # FancyLED can handle the gamma adjustment, brightness and RGB settings
        color = fancy.palette_lookup(palette, i / num_leds)
        color = fancy.gamma_adjust(color, brightness=brightness)
        strip[i] = color.pack()

        if i >= num_leds - 1:
            for j in range(concurrent,-1,-1):
                strip[i-j] = (0,0,0)

while True:

    # loop through each neopixel strip in our list
        led_drops(drop0)
