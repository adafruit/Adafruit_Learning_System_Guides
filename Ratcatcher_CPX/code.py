import board
import neopixel
from adafruit_led_animation.animation.pulse import Pulse

from adafruit_led_animation.color import WHITE

# Update to match the pin connected to your NeoPixels
pixel_pin = board.NEOPIXEL
# Update to match the number of NeoPixels you have connected
pixel_num = 10

pixels = neopixel.NeoPixel(pixel_pin, pixel_num, brightness=0.8, auto_write=False)

pulse = Pulse(pixels, speed=0.05, color=WHITE, period=5)

while True:
    pulse.animate()
