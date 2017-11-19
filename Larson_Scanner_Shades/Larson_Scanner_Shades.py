import board
import neopixel
import time

numpix = 22         # Number of NeoPixels
pixpin = board.D1   # Pin where NeoPixels are connected Gemma M0 = D1 | Trinket M0 = D4
strip  = neopixel.NeoPixel(pixpin, numpix, brightness=1, auto_write=False)
pos = 0             # position
direction = 1       # direction of "eye"

while True:
    strip[pos-2] = ([16,0,0])   # Dark red
    strip[pos-1] = ([128,0,0])  # Medium red
    strip[pos]   = ([255,48,0]) # brightest
    strip[pos+1] = ([128,0,0])  # Medium red

    if ( (pos + 2) < numpix ):
        strip[pos+2] = ([16,0,0])   # Dark red, do not exceed number of pixels 

    strip.write()
    time.sleep(0.03)

    # Rather than being sneaky and erasing just the tail pixel,
    # it's easier to erase it all and draw a new one next time.
    for j in range(-2, 2):
        strip[pos+j] = (0,0,0)
        if ( (pos + 2) < numpix ):
            strip[pos+2] = (0,0,0)

    # Bounce off ends of strip
    pos += direction
    if ( pos < 0 ):
        pos = 1
        direction = -direction
    elif ( pos >= (numpix - 1) ):
        pos = numpix - 2
        direction = -direction
