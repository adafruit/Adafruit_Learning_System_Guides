"""
FancyLED Necklace Insert Code
Written by Phil Burgess and Erin St Blaine for Adafruit Industries
Full tutorial: https://learn.adafruit.com/neopixel-led-necklace-insert-with-usb-charging

"""

import board
import neopixel
import adafruit_fancyled.adafruit_fancyled as fancy

NUM_LEDS = 15

# Define your palettes. Add as many colors as you like.
# You can use CRGB, CHSV or Hex format, or any combination therein
# Select which palette you're using below the palette definitions

palette_fire = [fancy.CRGB(0, 0, 0),        #Black
                fancy.CHSV(1.0),            #Red
                fancy.CRGB(1.0, 1.0, 0.0),  #Yellow
                0xFFFFFF,]                  #White


palette_water = [fancy.CRGB(0, 214, 214), # blues and cyans
                 fancy.CRGB(0, 92, 160),
                 fancy.CRGB(0, 123, 255),
                 fancy.CRGB(0, 100, 200),
                 fancy.CRGB(0, 120, 210),
                 fancy.CRGB(0, 123, 255),
                 fancy.CRGB(0, 68, 214),
                 fancy.CRGB(0, 68, 214),
                 fancy.CRGB(0, 28, 214),
                 fancy.CRGB(0, 68, 200),
                 fancy.CRGB(0, 68, 214),
                 fancy.CRGB(0, 200, 50),
                 fancy.CRGB(0, 200, 80),
                 fancy.CRGB(0, 200, 20),
                 fancy.CRGB(0, 100, 50),
                 fancy.CRGB(0, 150, 50),]

palette_forest = [0xa6db97,
                  0xc6de50,
                  0x2a7a02,
                  0x5fb862,
                  0x314a32,
                  0xd5e8d6,]

palette_cloud = [fancy.CHSV(0.8, 1.0, 1.0),
                 fancy.CHSV(0.6, 0.8, 0.7),
                 fancy.CHSV(0.7, 1.0, 0.8),]

#choose your active palette
palette = palette_water

# Declare a NeoPixel object on pin A1 with NUM_LEDS pixels, no auto-write.
# Set brightness to max because we'll be using FancyLED's brightness control.
pixels = neopixel.NeoPixel(board.A1, NUM_LEDS, brightness=1.0,
                           auto_write=False)

OFFSET = 0  # Positional offset into color palette to get it to 'spin'

while True:
    for i in range(NUM_LEDS):
        # Load each pixel's color from the palette using an offset, run it
        # through the gamma function, pack RGB value and assign to pixel.
        color = fancy.palette_lookup(palette, OFFSET + i / NUM_LEDS)
        color = fancy.gamma_adjust(color, brightness=0.25)
        pixels[i] = color.pack()
    pixels.show()

    OFFSET += 0.005  # Bigger number = faster spin
