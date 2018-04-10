# NeoPixel earrings example.  Makes a nice blinky display with just a
# few LEDs on at any time...uses MUCH less juice than rainbow display!

import board
import neopixel
import time
try:
	import urandom as random  # for v1.0 API support
except ImportError:
	import random

# The example is prepared both for RGB and RGBW (with an extra white)
# NeoPixel rings.  The RGBW requires the bpp=4 option (default is
# bpp=3).  This increases the number of bits per pixel compared to the
# RGB version.  The number of elements in the color value list is also
# different: [R, G, B] vs [R, G, B, W].  Pick the line that suits your
# NeoPixel ring.

numpix = 16  # Number of NeoPixels (e.g. 16-pixel ring)
pixpin = board.D0  # Pin where NeoPixels are connected
strip  = neopixel.NeoPixel(pixpin, numpix, brightness=.3) # for RGB
# strip  = neopixel.NeoPixel(pixpin, numpix, brightness=.3, bpp=4) # for RGBW

def wheel(pos):
	# Input a value 0 to 255 to get a color value.
	# The colours are a transition r - g - b - back to r.
	if (pos < 0) or (pos > 255):
		return [0, 0, 0] # for RGB
		# return [0, 0, 0, 0] # for RGBW
	elif (pos < 85):
		return [int(pos * 3), int(255 - (pos * 3)), 0] # for RGB
		# return [int(pos * 3), int(255 - (pos * 3)), 0, 0] # for RGBW
	elif (pos < 170):
		pos -= 85
		return [int(255 - pos * 3), 0, int(pos * 3)] # for RGB
		# return [int(255 - pos * 3), 0, int(pos * 3), 0] # for RGBW
	else:
		pos -= 170
		return [0, int(pos * 3), int(255 - pos * 3)] # for RGB
		# return [0, int(pos * 3), int(255 - pos * 3), 0] # for RGBW

mode     = 0  # Current animation effect
offset   = 0  # Position of spinner animation
hue      = 0  # Starting hue
color    = wheel(hue & 255)  # hue -> RGB color
prevtime = time.monotonic()  # Time of last animation mode switch

while True:  # Loop forever...

	if mode == 0:  # Random sparkles - lights just one LED at a time
		i = random.randint(0, numpix - 1)  # Choose random pixel
		strip[i] = color   # Set it to current color
		strip.write()      # Refresh LED states
		# Set same pixel to "off" color now but DON'T refresh...
		# it stays on for now...bot this and the next random
		# pixel will be refreshed on the next pass.
		strip[i] = [0,0,0] # for RGB
		# strip[i] = [0,0,0,0] # for RGBW
		time.sleep(0.008)  # 8 millisecond delay
	elif mode == 1:  # Spinny wheel (4 LEDs on at a time)
		for i in range(numpix):  # For each LED...
			if ((offset + i) & 7) < 2:  # 2 pixels out of 8...
				strip[i] = color    # are set to current color
			else:
				strip[i] = [0,0,0]  # other pixels are off, for RGB
				# strip[i] = [0,0,0,0]  # other pixels are off, for RGBW
		strip.write()    # Refresh LED states
		time.sleep(0.04) # 40 millisecond delay
		offset += 1      # Shift animation by 1 pixel on next frame
		if offset >= 8: offset = 0
	# Additional animation modes could be added here!

	t = time.monotonic()                # Current time in seconds
	if (t - prevtime) >= 8:             # Every 8 seconds...
		mode    += 1                # Advance to next mode
		if mode > 1:                # End of modes?
			mode  =  0          # Start over from beginning
			hue  += 80          # And change color
			color = wheel(hue & 255)
		strip.fill([0,0,0])         # Turn off all pixels, for RGB
		# strip.fill([0,0,0,0])       # Turn off all pixels, for RGBW
		prevtime = t                # Record time of last mode change
