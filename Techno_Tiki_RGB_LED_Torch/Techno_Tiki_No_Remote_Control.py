import time
import board
import neopixel

pixel_count = 6         # Number of NeoPixels
pixel_pin = board.D1    # Pin where NeoPixels are connected

speed = .1              # Animation speed (in seconds). 
                        # This is how long to spend in a single animation frame.  
                        # Higher values are slower.
                        # Good values to try are 400, 200, 100, 50, 25, etc.

animation = 0           # Type of animation, can be one of these values:
                        # 0 - Solid color pulse
                        # 1 - Moving color pulse

color_steps = 8         # Number of steps in the animation.

brightness = 1.0        # # 0-1, higher number is brighter

# Adjacent colors (on color wheel).
# Red-yellow
color_animation =   ([255, 0, 0], [255, 36, 0], [255, 72, 0], [255, 109, 0],
                    [255, 145, 0], [255, 182, 0], [255, 218, 0], [255, 255, 0])


# Global state used by the sketch
strip = neopixel.NeoPixel(pixpin, pixel_count, brightness=1, auto_write=False)

while True:  # Loop forever...
    for i range(pixel_count):
    # Main loop will update all the pixels based on the animation.

    # Animation 0, solid color pulse of all pixels.
    if animation == 0:
        current_Step = (millis() / speed)%(colorSteps*2-2);

    # Animation 1, moving color pulse.  Use position to change brightness.
    elif animation == 1:

    for i in range(pixel_count):
        color = color_animation
#        color = fancy.palette_lookup(color_animation, offset + i / pixel_count)
#        color = fancy.gamma_adjust(color, brightness=brightness)
        strip[i] = color.pack()
    strip.show()

    if fadeup:
        offset += steps
        if offset >= 1:
            fadeup = False
    else:
        offset -= steps
        if offset <= 0:
            fadeup = True
