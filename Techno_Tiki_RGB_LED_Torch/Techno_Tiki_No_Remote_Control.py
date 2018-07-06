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

    # Main loop will update all the pixels based on the animation.
    for i range(pixel_count):

        # Animation 0, solid color pulse of all pixels.
        if animation == 0:
            current_step = (time.monotonic() / speed) % (color_steps * 2 - 2)
            if (current_step >= color_steps):
                current_step = color_steps - (current_step - (colorSteps - 2))

        # Animation 1, moving color pulse.  Use position to change brightness.
        elif animation == 1:
            current_step = (time.monotonic() / speed + i) % (color_steps * 2 - 2);
            if (current_step >= color_steps):
                current_step = color_steps - (current_step - (colorSteps - 2))

        strip[i] = color_animation[current_step]

    # Show the updated pixels.
    strip.show()
