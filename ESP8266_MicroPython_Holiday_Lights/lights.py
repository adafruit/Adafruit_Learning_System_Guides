# ESP8266 MicroPython smart holiday lights project code.
# This will animate NeoPixels that can be controlled from the included
# lights.html web page.
# Author: Tony DiCola
# License: MIT License
import machine
import neopixel
import utime
import ujson


# Static configuration that never changes:
PIXEL_PIN   = machine.Pin(15, machine.Pin.OUT)  # Pin connected to the NeoPixels.
PIXEL_COUNT = 32                                # Number of NeoPixels.
CONFIG_FILE = 'config.json'                     # Name of animation config file.


# Mirror the colors to make a ramp up and ramp down with no repeated colors.
def mirror(values):
    # Add the input values in reverse order to the end of the array.
    # However slice off the very first and very last items (the [1:-1] syntax)
    # to prevent the first and last values from repeating.
    # For example an input of:
    #  [1, 2, 3]
    # Returns:
    #  [1, 2, 3, 2]
    # Instead of returning:
    #  [1, 2, 3, 3, 2, 1]
    # Which would duplicate 3 and 1 as you loop through the elements.
    values.extend(list(reversed(values))[1:-1])
    return values

# Linear interpolation helper:
def _lerp(x, x0, x1, y0, y1):
    return y0 + (x - x0) * ((y1 - y0)/(x1 - x0))


# Animation functions:
def blank(config, np, pixel_count):  # pylint: disable=unused-argument, redefined-outer-name
    # Turn off all the pixels.
    np.fill((0,0,0))
    np.write()


def solid(config, np, pixel_count):  # pylint: disable=unused-argument, redefined-outer-name
    # Solid pulse of all pixels at the same color.
    colors = config['colors']
    elapsed = utime.ticks_ms() // config['period_ms']
    current = elapsed % len(colors)
    np.fill(colors[current])
    np.write()


def chase(config, np, pixel_count):  # pylint: disable=unused-argument, redefined-outer-name
    # Chasing animation of pixels through different colors.
    colors = config['colors']
    elapsed = utime.ticks_ms() // config['period_ms']
    for i in range(PIXEL_COUNT):
        current = (elapsed+i) % len(colors)
        np[i] = colors[current]
    np.write()


def smooth(config, np, pixel_count):  # pylint: disable=unused-argument, redefined-outer-name
    # Smooth pulse of all pixels at the same color.  Interpolates inbetween colors
    # for smoother animation.
    colors = config['colors']
    period_ms = config['period_ms']
    ticks = utime.ticks_ms()
    step = ticks // period_ms
    offset = ticks % period_ms
    color0 = colors[step % len(colors)]
    color1 = colors[(step+1) % len(colors)]
    color = (int(_lerp(offset, 0, period_ms, color0[0], color1[0])),
             int(_lerp(offset, 0, period_ms, color0[1], color1[1])),
             int(_lerp(offset, 0, period_ms, color0[2], color1[2])))
    np.fill(color)
    np.write()


# Setup code:
# Initialize NeoPixels and turn them off.
np = neopixel.NeoPixel(PIXEL_PIN, PIXEL_COUNT)
np.fill((0,0,0))
np.write()

# Try loading the animation configuration, otherwise fall back to a blank default.
try:
    with open(CONFIG_FILE, 'r') as infile:
        config = ujson.loads(infile.read())
except OSError:
    # Couldn't load the config file, so fall back to a default blank animation.
    config = {
        'colors': [[0,0,0]],
        'mirror_colors': False,
        'period_ms': 250,
        'animation': 'blank'
    }

# Mirror the color array if necessary.
if config['mirror_colors']:
    config['colors'] = mirror(config['colors'])

# Determine which animation function should be called.
animation = globals().get(config['animation'], blank)

# Main loop code:
while True:
    animation(config, np, PIXEL_COUNT)
    utime.sleep(0.01)
