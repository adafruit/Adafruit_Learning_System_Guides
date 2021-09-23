import adafruit_fancyled.adafruit_fancyled as fancy
import board
import neopixel
from digitalio import DigitalInOut, Direction, Pull

led_pin = board.D1  # which pin your pixels are connected to
num_leds = 78  # how many LEDs you have
brightness = 1.0  # 0-1, higher number is brighter
saturation = 255  # 0-255, 0 is pure white, 255 is fully saturated color
steps = 0.01  # how wide the bands of color are.
offset = 0  # cummulative steps
fadeup = True  # start with fading up - increase steps until offset reaches 1
index = 8  # midway color selection
blend = True  # color blending between palette indices

# initialize list with all pixels off
palette = [0] * num_leds

# Declare a NeoPixel object on led_pin with num_leds as pixels
# No auto-write.
# Set brightness to max.
# We will be using FancyLED's brightness control.
strip = neopixel.NeoPixel(led_pin, num_leds, brightness=1, auto_write=False)

# button setup
button = DigitalInOut(board.D2)
button.direction = Direction.INPUT
button.pull = Pull.UP
prevkeystate = False
ledmode = 0  # button press counter, switch color palettes

# FancyLED allows for assigning a color palette using these formats:
# * The first (5) palettes here are mixing between 2-elements
# * The last (3) palettes use a format identical to the FastLED Arduino Library
# see FastLED - colorpalettes.cpp
forest = [fancy.CRGB(0, 255, 0),  # green
          fancy.CRGB(255, 255, 0)]  # yellow

ocean = [fancy.CRGB(0, 0, 255),  # blue
         fancy.CRGB(0, 255, 0)]  # green

purple = [fancy.CRGB(160, 32, 240),  # purple
          fancy.CRGB(238, 130, 238)]  # violet

all_colors = [fancy.CRGB(0, 0, 0),  # black
              fancy.CRGB(255, 255, 255)]  # white

washed_out = [fancy.CRGB(0, 0, 0),  # black
              fancy.CRGB(255, 0, 255)]  # purple

rainbow = [0xFF0000, 0xD52A00, 0xAB5500, 0xAB7F00,
           0xABAB00, 0x56D500, 0x00FF00, 0x00D52A,
           0x00AB55, 0x0056AA, 0x0000FF, 0x2A00D5,
           0x5500AB, 0x7F0081, 0xAB0055, 0xD5002B]

rainbow_stripe = [0xFF0000, 0x000000, 0xAB5500, 0x000000,
                  0xABAB00, 0x000000, 0x00FF00, 0x000000,
                  0x00AB55, 0x000000, 0x0000FF, 0x000000,
                  0x5500AB, 0x000000, 0xAB0055, 0x000000]

heat_colors = [0x330000, 0x660000, 0x990000, 0xCC0000, 0xFF0000,
               0xFF3300, 0xFF6600, 0xFF9900, 0xFFCC00, 0xFFFF00,
               0xFFFF33, 0xFFFF66, 0xFFFF99, 0xFFFFCC]


def remapRange(value, leftMin, leftMax, rightMin, rightMax):
    # this remaps a value fromhere original (left) range to new (right) range
    # Figure out how 'wide' each range is
    leftSpan = leftMax - leftMin
    rightSpan = rightMax - rightMin

    # Convert the left range into a 0-1 range (int)
    valueScaled = int(value - leftMin) / int(leftSpan)

    # Convert the 0-1 range into a value in the right range.
    return int(rightMin + (valueScaled * rightSpan))


def shortkeypress(color_palette):
    color_palette += 1

    if color_palette > 6:
        color_palette = 1

    return color_palette


while True:

    # check for button press
    currkeystate = button.value

    # button press, move to next pattern
    if (prevkeystate is not True) and currkeystate:
        ledmode = shortkeypress(ledmode)

    # save button press state
    prevkeystate = currkeystate

    # Fire Colors [ HEAT ]
    if ledmode == 1:
        palette = heat_colors

    # Forest
    elif ledmode == 2:
        palette = forest

    # Ocean
    elif ledmode == 3:
        palette = ocean

    # Purple Lovers
    elif ledmode == 4:
        palette = purple

    # All the colors!
    elif ledmode == 5:
        palette = rainbow

    # Rainbow stripes
    elif ledmode == 6:
        palette = rainbow_stripe

    # All the colors except the greens, washed out
    elif ledmode == 7:
        palette = washed_out

    for i in range(num_leds):
        color = fancy.palette_lookup(palette, offset + i / num_leds)
        color = fancy.gamma_adjust(color, brightness=brightness)
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
