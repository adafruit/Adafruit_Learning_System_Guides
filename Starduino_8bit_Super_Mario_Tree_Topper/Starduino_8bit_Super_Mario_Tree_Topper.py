import board
import neopixel
import adafruit_fancyled.adafruit_fancyled as fancy

num_leds = 16       # number of LEDs per strip
saturation = 255    # 0-255, 0 is pure white, 255 is fully saturated color
blend = True        # color blending between palette indices
brightness = 0.8    # brightness the range is 0.0 - 1.0
flicker = 0          # flame flicker

# NeoPixel objects using
leds = neopixel.NeoPixel(board.D0, num_leds)

# Inspired by Fire2012() by Mark Kriegsman and his use of FastLED
# to create a one-dimensional 'fire' simulation
# the heat colors are from the heat palette that FastLED provides
def fire_2018(strip, offset):
    # heat colors
    palette = [0x330000, 0x660000, 0x990000, 0xCC0000, 0xFF0000,
               0xFF3300, 0xFF6600, 0xFF9900, 0xFFCC00, 0xFFFF00,
               0xFFFF33, 0xFFFF66, 0xFFFF99, 0xFFFFCC]

    for i in range(num_leds):
        # FancyLED can handle the gamma adjustment, brightness and RGB settings
        color = fancy.palette_lookup(palette, offset + i / num_leds)
        color = fancy.gamma_adjust(color, brightness=brightness)
        strip[i] = color.pack()

while True:
    fire_2018(leds, flicker)
    flicker += 0.3           # flame flicker, adjust value to control speed
