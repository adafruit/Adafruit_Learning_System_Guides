import time
import board
import neopixel

pixpin = board.D1
numpix = 60

strip = neopixel.NeoPixel(pixpin, numpix, brightness=1, auto_write=True)

# Fill the dots one after the other with a color
def colorWipe(color, wait):
    for j in range(len(strip)):
        strip[j] = (color)
        time.sleep(wait)

def wheel(pos):
    # Input a value 0 to 255 to get a color value.
    # The colours are a transition r - g - b - back to r.
    if (pos < 0) or (pos > 255):
        return (0, 0, 0)
    if pos < 85:
        return (int(pos * 3), int(255 - (pos * 3)), 0)
    elif pos < 170:
        pos -= 85
        return (int(255 - pos * 3), 0, int(pos * 3))

    pos -= 170
    return (0, int(pos * 3), int(255 - pos * 3))

def rainbow_cycle(wait):
    for j in range(255):
        for i in range(len(strip)):
            idx = int((i * 256 / len(strip)) + j)
            strip[i] = wheel(idx & 255)
        time.sleep(wait)

def rainbow(wait):
    for j in range(255):
        for i in range(len(strip)):
            idx = int(i + j)
            strip[i] = wheel(idx & 255)
        time.sleep(wait)

while True:
    colorWipe((255, 0, 0), .05)  # red and delay
    colorWipe((0, 255, 0), .05)  # green and delay
    colorWipe((0, 0, 255), .05)  # blue and delay

    rainbow(0.02)
    rainbow_cycle(0.02)
