# Bright Wearables Purse Slideshow with FancyLED
# Anne Barela for Adafruit Industries, February 2020
# MIT License

import time
import board
import adafruit_dotstar as dotstar
from adafruit_clue import clue
from adafruit_slideshow import SlideShow, PlayBackDirection
import adafruit_fancyled.adafruit_fancyled as fancy

slideshow = SlideShow(clue.display, None, folder="/",
                      auto_advance=False, dwell=0)

# For the Bright Wearables DotStar LED Ring
num_leds = 12
palette = [fancy.CRGB(1.0, 0.0, 0.5),  # Pink
           fancy.CRGB(0.0, 1.0, 0.0),  # Green
           fancy.CRGB(0.0, 0.0, 1.0)]  # Blue
pixels = dotstar.DotStar(board.P13, board.P15, num_leds, brightness=0.5,
                         auto_write=False)
offset = 0  # Initialize the offset for variation (twinkle)

while True:
    if clue.button_b:
        slideshow.direction = PlayBackDirection.FORWARD
        slideshow.advance()
    if clue.button_a:
        slideshow.direction = PlayBackDirection.BACKWARD
        slideshow.advance()
    for i in range(num_leds):
        # Load each pixel's color from the palette using an offset, run it
        # through the gamma function, pack RGB value and assign to pixel.
        color = fancy.palette_lookup(palette, offset + i / num_leds)
        color = fancy.gamma_adjust(color, brightness=0.25)
        pixels[i] = color.pack()
    pixels.show()
    offset = offset + 1
    if offset > 12:
        offset = 0
    time.sleep(0.1)
