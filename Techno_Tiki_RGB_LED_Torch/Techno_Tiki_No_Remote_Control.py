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

brightness = 1.0        # 0-1, higher number is brighter


# Adjacent colors (on color wheel).
# red yellow
color_animation = ([255, 0, 0], [255, 36, 0], [255, 72, 0], [255, 109, 0],
                   [255, 145, 0], [255, 182, 0], [255, 218, 0], [255, 255, 0])

# Adjacent colors
#([255, 0, 0], [255, 36, 0], [255, 72, 0], [255, 109, 0],
# [255, 145, 0], [255, 182, 0], [255, 218, 0], [255, 255, 0])           # red yellow
#([255, 255, 0], [218, 255, 0], [182, 255, 0], [145, 255, 0],
# [109, 255, 0], [72, 255, 0], [36, 255, 0], [0, 255, 0])               # yello green
#([0, 255, 0], [0, 255, 36], [0, 255, 72], [0, 255, 109],
# [0, 255, 145], [0, 255, 182], [0, 255, 218], [0, 255, 255])           # green cyan
#([0, 255, 255], [0, 218, 255], [0, 182, 255], [0, 145, 255],
# [0, 109, 255], [0, 72, 255], [0, 36, 255], [0, 0, 255])               # cyan blue
#([0, 0, 255], [36, 0, 255], [72, 0, 255], [109, 0, 255],
# [145, 0, 255], [182, 0, 255], [218, 0, 255], [255, 0, 255])           # blue magenta
#([255, 0, 255], [255, 0, 218], [255, 0, 182], [255, 0, 145],
# [255, 0, 109], [255, 0, 72], [255, 0, 36], [255, 0, 0])               # magenta red

# Complimentary colors
#([255, 0, 0], [218, 36, 36], [182, 72, 72], [145, 109, 109],
# [109, 145, 145], [72, 182, 182], [36, 218, 218], [0, 255, 255])       # red cyan
#([255, 255, 0], [218, 218, 36], [182, 182, 72], [145, 145, 109],
# [109, 109, 145], [72, 72, 182], [36, 36, 218], [0, 0, 255])           # yellow blue
#([0, 255, 0], [36, 218, 36], [72, 182, 72], [109, 145, 109],
# [145, 109, 145], [182, 72, 182], [218, 36, 218], [255, 0, 255])       # green magenta

# Other combos
#([255, 0, 0], [218, 36, 0], [182, 72, 0], [145, 109, 0],
# [109, 145, 0], [72, 182, 0], [36, 218, 0], [0, 255, 0])               # red green
#([255, 255, 0], [218, 255, 36], [182, 255, 72], [145, 255, 109],
# [109, 255, 145], [72, 255, 182], [36, 255, 218], [0, 255, 255])       # yellow cyan
#([0, 255, 0], [0, 218, 36], [0, 182, 72], [0, 145, 109],
# [0, 109, 145], [0, 72, 182], [0, 36, 218], [0, 0, 255])               # green blue
#([0, 255, 255], [36, 218, 255], [72, 182, 255], [109, 145, 255],
# [145, 109, 255], [182, 72, 255], [218, 36, 255], [255, 0, 255])       # cyan magenta
#([0, 0, 255], [36, 0, 218], [72, 0, 182], [109, 0, 145],
# [145, 0, 109], [182, 0, 72], [218, 0, 36], [255, 0, 0])               # blue red
#([255, 0, 255], [255, 36, 218], [255, 72, 182], [255, 109, 145],
# [255, 145, 109], [255, 182, 72], [255, 218, 36], [255, 255, 0])       # magenta yellow

# Solid colors fading to dark
#([255, 0, 0], [223, 0, 0], [191, 0, 0], [159, 0, 0],
# [127, 0, 0], [95, 0, 0], [63, 0, 0], [31, 0, 0])                      #  red
#([255, 153, 0], [223, 133, 0], [191, 114, 0], [159, 95, 0],
# [127, 76, 0], [95, 57, 0], [63, 38, 0], [31, 19, 0])                  # orange
#([255, 255, 0], [223, 223, 0], [191, 191, 0], [159, 159, 0],
# [127, 127, 0], [95, 95, 0], [63, 63, 0], [31, 31, 0])                 # yellow
#([0, 255, 0], [0, 223, 0], [0, 191, 0], [0, 159, 0],
# [0, 127, 0], [0, 95, 0], [0, 63, 0], [0, 31, 0])                      # green
#([0, 0, 255], [0, 0, 223], [0, 0, 191], [0, 0, 159],
# [0, 0, 127], [0, 0, 95], [0, 0, 63], [0, 0, 31])                      # blue
#([75, 0, 130], [65, 0, 113], [56, 0, 97], [46, 0, 81],
# [37, 0, 65], [28, 0, 48], [18, 0, 32], [9, 0, 16])                    # indigo
#([139, 0, 255], [121, 0, 223], [104, 0, 191], [86, 0, 159],
# [69, 0, 127], [52, 0, 95], [34, 0, 63], [17, 0, 31])                  # violet
#([255, 255, 255], [223, 223, 223], [191, 191, 191], [159, 159, 159],
# [127, 127, 127], [95, 95, 95], [63, 63, 63], [31, 31, 31])            # white
#([255, 0, 0], [255, 153, 0], [255, 255, 0], [0, 255, 0],
# [0, 0, 255], [75, 0, 130], [139, 0, 255], [255, 255, 255])            # rainbow colors

# Global state used by the sketch
strip = neopixel.NeoPixel(pixel_pin, pixel_count, brightness=1, auto_write=False)

while True:  # Loop forever...

    # Main loop will update all the pixels based on the animation.
    for i in range(pixel_count):

        # Animation 0, solid color pulse of all pixels.
        if animation == 0:
            current_step = (time.monotonic() / speed) % (color_steps * 2 - 2)
            if current_step >= color_steps:
                current_step = color_steps - (current_step - (color_steps - 2))

        # Animation 1, moving color pulse.  Use position to change brightness.
        elif animation == 1:
            current_step = (time.monotonic() / speed + i) % (color_steps * 2 - 2)
            if current_step >= color_steps:
                current_step = color_steps - (current_step - (color_steps - 2))

        strip[i] = color_animation[int(current_step)]

    # Show the updated pixels.
    strip.show()
