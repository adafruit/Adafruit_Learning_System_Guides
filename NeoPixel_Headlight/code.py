import time
import board
import pulseio
import simpleio
from digitalio import DigitalInOut, Direction, Pull
import adafruit_fancyled.adafruit_fancyled as fancy
import neopixel

NEOPIXEL_PIN = board.D6
NEOPIXEL_NUM = 31
pixels = neopixel.NeoPixel(NEOPIXEL_PIN, NEOPIXEL_NUM, auto_write=False)

# Since its common anode, 'off' is max duty cycle
red_led = pulseio.PWMOut(board.D9, frequency=5000, duty_cycle=65535)
green_led = pulseio.PWMOut(board.D10, frequency=5000, duty_cycle=65535)
blue_led = pulseio.PWMOut(board.D11, frequency=5000, duty_cycle=65535)

switch = DigitalInOut(board.D12)
switch.direction = Direction.INPUT
switch.pull = Pull.UP

colorways = [fancy.CRGB(1.0, 1.0, 1.0), # White
             fancy.CRGB(1.0, 0.0, 0.0), # Red
             fancy.CRGB(0.5, 0.5, 0.0), # Yellow
             fancy.CRGB(0.0, 1.0, 0.0), # Green
             fancy.CRGB(0.0, 0.5, 0.5), # Cyan
             fancy.CRGB(0.0, 0.0, 1.0), # Blue
             fancy.CRGB(0.5, 0.0, 0.5), # Magenta
             # you can also make lists of colors to cycle through, like red/green/blue:
             [fancy.CRGB(1.0, 0.0, 0.0), fancy.CRGB(0.0, 1.0, 0.0), fancy.CRGB(0.0, 0.0, 1.0)],
             # or just white/blue
             [fancy.CRGB(1.0, 1.0, 1.0), fancy.CRGB(0.0, 0.0, 1.0)],
            ]
color_index = 0

def set_rgb_led(color):
    # convert from 0-255 (neopixel range) to 65535-0 (pwm range)
    red_led.duty_cycle = int(simpleio.map_range(color[0], 0, 255, 65535, 0))
    green_led.duty_cycle = int(simpleio.map_range(color[1], 0, 255, 65535, 0))
    blue_led.duty_cycle = int(simpleio.map_range(color[2], 0, 255, 65535, 0))

while True:
    colorway = colorways[color_index]
    if not isinstance(colorway, list):
        print("Setting pixels to RGB", colorway)
        pixels.fill(colorway.pack())
        pixels.show()
        set_rgb_led(pixels[0])    # set RGB LED as same as first pixel

    else:
        # its a list of colors to cycle through
        print("Setting pixels to a pallete of", colorway)
        swirl = 0  # we'll swirl through the colors in the color way
        while switch.value:                     # button pressed? quit!
            for i in range(NEOPIXEL_NUM):
                # the index into the palette is from 0 to 1.0 and uses the pixels
                # number and the swirl number to take us through the whole thing!
                pallete_index = ((swirl+i) % NEOPIXEL_NUM) / NEOPIXEL_NUM
                # Then look up the color in the pallete
                color_lookup = fancy.palette_lookup(colorway, pallete_index)
                # display it!
                pixels[i] = color_lookup.pack()
                # check button often
                if not switch.value:
                    break             # if its pressed, quit now
            pixels.show()             # show the pixels!
            set_rgb_led(pixels[0])    # set RGB LED as same as first pixel
            swirl += 1                # never stop swirlin!
        print('Done with pallete display')

    while switch.value:
        pass  # hang out and wait for the button to be pressed
    while not switch.value:
        pass  # hang out and wait for the button to be released!
    print("Button pressed")
    # go to the next colorway
    color_index = (color_index + 1) % len(colorways)
    # a little debouncin' delay
    time.sleep(0.01)
