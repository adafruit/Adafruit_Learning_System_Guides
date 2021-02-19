import random
from adafruit_led_animation.animation.rainbowcomet import RainbowComet
from adafruit_led_animation.helper import PixelMap
from adafruit_led_animation.group import AnimationGroup
from neopio import NeoPIO
import board

# Customize for your strands here
num_strands = 8
strand_length = 30

# Make the object to control the pixels
pixels = NeoPIO(board.GP0, board.GP1, board.GP2, num_strands*strand_length,
    num_strands=num_strands, auto_write=False, brightness=.18)

# Make a virtual PixelMap so that each strip can be controlled independently
strips = [PixelMap(pixels, range(i*30, (i+1)*30), individual_pixels=True)
    for i in range(num_strands)]

# This function makes a comet animation with slightly random settings
def make_animation(strip):
    speed = (1+random.random()) * 0.02
    length = random.randrange(18, 22)
    bounce = random.random() > .5
    offset = random.randint(0, 255)
    return RainbowComet(strip, speed=speed, tail_length=length, bounce=bounce,
        colorwheel_offset=offset)

# Make an animation for each virtual strip
animations = [make_animation(strip) for strip in strips]

# Put the animations into a group so that we can animate them together
group = AnimationGroup(*animations, )

# Show the animations forever
while True:
    group.animate()
