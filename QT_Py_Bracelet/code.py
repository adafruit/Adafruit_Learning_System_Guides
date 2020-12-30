# Demo code to generate an alternating color-gradient effect in
# the QT Py LED cuff bracelet LEDs.
import time
import board
import neopixel

# Total number of LEDs on both strips
NUM_PIXELS = 14

pixels = neopixel.NeoPixel(board.MOSI, NUM_PIXELS, pixel_order=neopixel.GRB, auto_write=False, brightness = 0.4
)

def wheel(pos):
    # Input a value 0 to 255 to get a color value.
    # The colours are a transition r - g - b - back to r.
    if pos < 0 or pos > 255:
        return (0, 0, 0)
    if pos < 85:
        return (255 - pos * 3, pos * 3, 0)
    if pos < 170:
        pos -= 85
        return (0, 255 - pos * 3, pos * 3)
    pos -= 170
    return (pos * 3, 0, 255 - pos * 3)
    
# Scales a tuple by a fraction of 255
def scale(tup, frac):
    return tuple((x*frac)//255 for x in tup)

# Sawtooth function with amplitude and period of 255
def sawtooth(x):
    return int(2*(127.5 - abs((x % 255) - 127.5)))

# Hue value at the opposite side of the color wheel
def oppositeHue(x):
    return ((x + 128) % 256)

hueIndex = 0         # determines hue value (0->255)
brightnessIndex = 0  # input to the sawtooth function for determining brightness (0->255)
brightnessSpeed = 3  # bigger value = faster shifts in brightness

while True:
    bright = sawtooth(brightnessIndex)
    
    # get RGB color from wheel function and scale it by the brightness
    mainColor = scale(wheel(hueIndex),bright)
    oppColor = scale(wheel(oppositeHue(hueIndex)), 255 - bright)

    # hue and brightness alternate along each strip
    for i in range(NUM_PIXELS//2):
        pixels[i*2] = mainColor
        pixels[i*2 + 1] = oppColor
    pixels.show()
    
    # increment hue and brightness
    hueIndex = (hueIndex + 1) % 255        
    brightnessIndex = (brightnessIndex + brightnessSpeed) % 255
