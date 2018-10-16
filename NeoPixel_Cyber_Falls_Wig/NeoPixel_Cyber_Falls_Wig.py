import adafruit_fancyled.adafruit_fancyled as fancy
import board
import neopixel
import time
from digitalio import DigitalInOut, Direction, Pull

num_leds = 10       # number of LEDs per strip
saturation = 255    # 0-255, 0 is pure white, 255 is fully saturated color
blend = True        # color blending between palette indices
brightness = 0.1
concurrent = 2
on_time = 0.04      # 40ms

# initialize list with all pixels off
palette = [0] * num_leds

# NeoPixel objects with led_pin and number of LEDs
drop0 = neopixel.NeoPixel(board.D0, num_leds)
drop1 = neopixel.NeoPixel(board.D1, num_leds)
drop2 = neopixel.NeoPixel(board.D2, num_leds)
drop3 = neopixel.NeoPixel(board.D3, num_leds)
drop4 = neopixel.NeoPixel(board.D4, num_leds)

# list of strips
drop_list = [drop0, drop1, drop2, drop3, drop4]

# FancyLED allows for assigning a color palette using these formats:
# see FastLED - colorpalettes.cpp
def led_drops(strip):

    palette = [fancy.CRGB(150, 255, 150),          # lighter green
                fancy.CRGB(0, 255, 0)]        # full green

    for i in range(num_leds):
        color = fancy.palette_lookup(palette, i / num_leds)
        color = fancy.gamma_adjust(color, brightness=brightness)
        strip[i] = color.pack()

        if  i >= concurrent:
            strip[i - concurrent] = (0,0,0)

        if i >= num_leds - 1:
            for j in range(concurrent,-1,-1):
                strip[i-j] = (0,0,0)
                time.sleep(on_time)

        time.sleep(on_time)

    
while True:

    for strip in drop_list:
        led_drops(strip)
