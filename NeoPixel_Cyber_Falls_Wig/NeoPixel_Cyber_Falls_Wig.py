import adafruit_fancyled.adafruit_fancyled as fancy
import board
import neopixel
import time
from digitalio import DigitalInOut, Direction, Pull

led_pin = board.D0  # which pin your pixels are connected to
num_leds = 16       # how many LEDs you have
brightness = .1     # 0-1, higher number is brighter
saturation = 255 # 0-255, 0 is pure white, 255 is fully saturated color
blend = True  # color blending between palette indices
simultaneous_leds = 8
duration_on = 0.04     # 40ms

# initialize list with all pixels off
palette = [0] * num_leds

# Declare a NeoPixel object on led_pin with num_leds as pixels
# No auto-write.
# Set brightness to max.
# We will be using FancyLED's brightness control.
strip = neopixel.NeoPixel(led_pin, num_leds, brightness=1)

# FancyLED allows for assigning a color palette using these formats:
# see FastLED - colorpalettes.cpp

while True:

    palette = [fancy.CRGB(150, 255, 150),          # lighter green
                fancy.CRGB(0, 255, 0)]        # full green

    for i in range(num_leds):
        color = fancy.palette_lookup(palette, i / num_leds)
        color = fancy.gamma_adjust(color, brightness=brightness)
        strip[i] = color.pack()

        if  simultaneous_leds <= i >= (num_leds - simultaneous_leds):
            strip[i - simultaneous_leds] = (0,0,0)

        if i >= num_leds - 1:
            for j in range(simultaneous_leds,-1,-1):
                strip[i-j] = (0,0,0)
                time.sleep(duration_on)

        time.sleep(duration_on)

    time.sleep(1)
