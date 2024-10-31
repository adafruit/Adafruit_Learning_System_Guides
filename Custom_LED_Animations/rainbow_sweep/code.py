import board
import neopixel

from rainbowsweep import RainbowSweepAnimation

# Update to match the pin connected to your NeoPixels
pixel_pin = board.D10
# Update to match the number of NeoPixels you have connected
pixel_num = 32

# initialize the neopixels. Change out for dotstars if needed.
pixels = neopixel.NeoPixel(pixel_pin, pixel_num, brightness=0.02, auto_write=False)

# initialize the animation
rainbowsweep = RainbowSweepAnimation(pixels, speed=0.05, color=0x000000, sweep_speed=0.1,
                                     sweep_direction=RainbowSweepAnimation.DIRECTION_END_TO_START)

while True:
    # call animation to show the next animation frame
    rainbowsweep.animate()
