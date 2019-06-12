# Image converter script for POV LED poi project.  Reads one or more images
# as input, generates tables which can be copied-and-pasted or redirected
# to a .h file, e.g.:
#
# $ python convert.py image1.gif image2.png > graphics.h
#
# Ideal image dimensions are determined by hardware setup, e.g. LED poi
# project uses 16 LEDs, so image height should match.  Width is limited
# by AVR PROGMEM capacity -- very limited on Trinket!
#
# Adafruit invests time and resources providing this open source code,
# please support Adafruit and open-source hardware by purchasing
# products from Adafruit!
#
# Written by Phil Burgess / Paint Your Dragon for Adafruit Industries.
# MIT license, all text above must be included in any redistribution.
# See 'COPYING' file for additional notes.
# --------------------------------------------------------------------------

from PIL import Image
import sys

# Establish peak and average current limits - a function of battery
# capacity and desired run time.

# These you can edit to match your build:
batterySize    = 150  # Battery capacity, in milliamp-hours (mAh)
runTime        = 1.1  # Est. max run time, in hours (longer = dimmer LEDs)
parallelStrips = 2    # Same data is issued to this many LED strips

# These probably don't need editing:
mcuCurrent     = 20   # Est. current used by microcontrolled board (mA)
wireLimit      = 1500 # Ampacity of battery wires (est 26 gauge) (milliamps)

# Estimate average and peak LED currents, within some safety thresholds:
if(runTime < 1.0): runTime = 1.0        # Don't exceed 1C rate from battery
cl = batterySize - mcuCurrent * runTime # After MCU, charge left for LEDs
if cl < 0: cl = 0                       # Must be non-negative
avgC = cl / runTime / parallelStrips
if avgC > wireLimit: avgC = wireLimit   # Don't exceed battery wire ampacity
peakC = avgC * 2.2                      # Battery+wires OK w/brief peaks

bR    = 1.0       # Can adjust
bG    = 1.0       # color balance
bB    = 1.0       # for whiter whites!
gamma = 2.7       # For more linear-ish perceived brightness

# Current estimates are averages measured from strip on LiPoly cell
mA0   =  1.3      # LED current when off (driver logic still needs some)
mAR   = 15.2 * bR # + current for 100% red
mAG   =  8.7 * bG # + current for 100% green
mAB   =  8.0 * bB # + current for 100% blue

# --------------------------------------------------------------------------

cols     = 0 # Current column number in output
byteNum  = 0
numBytes = 0

def writeByte(n):
	global cols, byteNum, numBytes

	cols += 1                      # Increment column #
	if cols >= 8:                  # If max column exceeded...
		print                  # end current line
		sys.stdout.write("  ") # and start new one
		cols = 0               # Reset counter
	sys.stdout.write("{0:#0{1}X}".format(n, 4))
	byteNum += 1
	if byteNum < numBytes:
		sys.stdout.write(",")
		if cols < 7:
			sys.stdout.write(" ")

# --------------------------------------------------------------------------

numLEDs = 0
images  = []

# Initial pass loads each image & tracks tallest size overall

for name in sys.argv[1:]: # For each image passed to script...
	image        = Image.open(name)
	image.pixels = image.load()
	# Determine if image is truecolor vs. colormapped.
	image.colors = image.getcolors(256)
	if image.colors == None:
		image.numColors = 257 # Image is truecolor
	else:
		# If 256 colors or less, that doesn't necessarily mean
		# it's a non-truecolor image yet, just that it has few
		# colors.  Check the image type and if it's truecolor or
		# similar, convert the image to a paletted mode so it can
		# be more efficiently stored.  Since there are few colors,
		# this operation is lossless.
		if (image.mode != '1' and image.mode != 'L' and
		  image.mode != 'P'):
			image = image.convert("P", palette="ADAPTIVE")
			image.pixels = image.load()
			image.colors = image.getcolors(256)
		# image.colors is an unsorted list of tuples where each
		# item is a pixel count and a color palette index.
		# Unused palette indices (0 pixels) are not in list,
		# so its length tells us the unique color count...
		image.numColors = len(image.colors)
		# The image & palette aren't necessarily optimally packed,
		# e.g. might have a 216-color 'web safe' palette but only
		# use a handful of colors.  In order to reduce the palette
		# storage requirements, only the colors in use will be
		# output.  The pixel indices in the image must be remapped
		# to this new palette sequence...
		remap = [0] * 256
		for c in range(image.numColors): # For each color used...
			# The original color index (image.colors[c][1])
			# is reassigned to a sequential 'packed' index (c):
			remap[image.colors[c][1]] = c
		# Every pixel in image is then remapped through this table:
		for y in range(image.size[1]):
			for x in range(image.size[0]):
				image.pixels[x, y] = remap[image.pixels[x, y]]
		# The color palette associated with the image is still in
		# its unpacked/unoptimal order; image pixel values no longer
		# point to correct entries.  This is OK and we'll compensate
		# for it later in the code.
	image.name = name
	image.bph  = image.size[1] # Byte-padded height (tweaked below)
	images.append(image)

	# 1- and 4-bit images are padded to the next byte boundary.
	# Image size not fully validated - on purpose - in case of quick
	# test with an existing (but non-optimal) file.  If too big or too
	# small for the LED strip, just wastes some PROGMEM space or some
	# LEDs will be lit wrong, usually no biggie.
	if image.numColors <= 2:    # 1 bit/pixel, use 8-pixel blocks
		if image.bph & 7: image.bph += 8 - (image.bph & 7)
	elif image.numColors <= 16: # 4 bits/pixel, use 2-pixel blocks
		if image.bph & 1: image.bph += 1

	if image.bph > numLEDs: numLEDs = image.bph

print "// Don't edit this file!  It's software-generated."
print "// See convert.py script instead."
print
print "#define PALETTE1  0"
print "#define PALETTE4  1"
print "#define PALETTE8  2"
print "#define TRUECOLOR 3"
print
print "#define NUM_LEDS %d" % numLEDs
print

# Second pass estimates current of each column, then peak & overall average

for imgNum, image in enumerate(images): # For each image in list...
	sys.stdout.write("// %s%s\n\n" % (image.name,
	  ' '.ljust(73 - len(image.name),'-')))
	if image.numColors <= 256:
		# Palette optimization requires some weird shenanigans...
		# first, make a duplicate image where width=image.numColors
		# and height=1.  This will have the same color palette as
		# the original image, which may contain many unused entries.
		lut = image.resize((image.numColors, 1))
		lut.pixels = lut.load()
		# The image.colors[] list contains the original palette
		# indices of the colors actually in use.  Draw one pixel
		# into the 'lut' image for each color index in use, in the
		# order they appear in the color list...
		for x in range(image.numColors):
			lut.pixels[x, 0] = image.colors[x][1]
		# ...then convert the lut image to RGB format to provide a
		# list of (R,G,B) values representing the packed color list.
		lut = list(lut.convert("RGB").getdata())

		# Estimate current for each element of palette:
		paletteCurrent = []
		for i in range(image.numColors):
			paletteCurrent.append(mA0 +
			  pow((lut[i][0] / 255.0), gamma) * mAR +
			  pow((lut[i][1] / 255.0), gamma) * mAG +
			  pow((lut[i][2] / 255.0), gamma) * mAB)

	# Estimate peak and average current for each column of image
	colMaxC = 0.0 # Maximum column current
	colAvgC = 0.0 # Average column current
	for x in range(image.size[0]): # For each row...
		mA = 0.0 # Sum current of each pixel's palette entry
		for y in range(image.size[1]):
			if image.numColors <= 256:
				mA += paletteCurrent[image.pixels[x, y]]
			else:
				mA += (mA0 +
				  pow((image.pixels[x, y][0] / 255.0),
				  gamma) * mAR +
				  pow((image.pixels[x, y][1] / 255.0),
				  gamma) * mAG +
				  pow((image.pixels[x, y][2] / 255.0),
				  gamma) * mAB)
		colAvgC += mA                 # Accumulate average (div later)
		if mA > colMaxC: colMaxC = mA # Monitor peak
	colAvgC /= image.size[0] # Sum div into average

	s1 = peakC / colMaxC   # Scaling factor for peak current constraint
	s2 = avgC  / colAvgC   # Scaling factor for average current constraint
	if s2 < s1:  s1 = s2   # Use smaller of two (so both constraints met),
	if s1 > 1.0: s1 = 1.0  # but never increase brightness

	s1 *= 255.0   # (0.0-1.0) -> (0.0-255.0)
	bR1 = bR * s1 # Scale color balance values
	bG1 = bG * s1
	bB1 = bB * s1

	p        = 0 # Current pixel number in image
	cols     = 7 # Force wrap on 1st output
	byteNum  = 0

	if image.numColors <= 256:
		# Output gamma- and brightness-adjusted color palette:
		print ("const uint8_t PROGMEM palette%02d[][3] = {" % imgNum)
		for i in range(image.numColors):
			sys.stdout.write("  { %3d, %3d, %3d }" % (
			  int(pow((lut[i][0]/255.0),gamma)*bR1+0.5),
			  int(pow((lut[i][1]/255.0),gamma)*bG1+0.5),
			  int(pow((lut[i][2]/255.0),gamma)*bB1+0.5)))
			if i < (image.numColors - 1): print ","
		print " };"
		print

		sys.stdout.write(
		  "const uint8_t PROGMEM pixels%02d[] = {" % imgNum)

		if image.numColors <= 2:
			numBytes = image.size[0] * numLEDs / 8
		elif image.numColors <= 16:
			numBytes = image.size[0] * numLEDs / 2
		elif image.numColors <= 256:
			numBytes = image.size[0] * numLEDs
		else:
			numBytes = image.size[0] * numLEDs * 3

		for x in range(image.size[0]):
			if image.numColors <= 2:
				for y in range(0, numLEDs, 8):
					sum = 0
					for bit in range(8):
						y1 = y + bit
						if y1 < image.size[1]:
							sum += (
							  image.pixels[x,
							  y1] << bit)
					writeByte(sum)
			elif image.numColors <= 16:
				for y in range(0, numLEDs, 2):
					if y < image.size[1]:
						p1 = image.pixels[x, y]
					else:
						p1 = 0
					if (y + 1) < image.size[1]:
						p2 = image.pixels[x, y + 1]
					else:
						p2 = 0
					writeByte(p1 * 16 + p2)
			elif image.numColors <= 256:
				for y in range(numLEDs):
					if y < image.size[1]:
						writeByte(image.pixels[x, y])
					else:
						writeByte(0)
			else:
				for y in range(numLEDs):
					if y < image.size[1]:
						writeByte(image.pixels[x, y][0])
						writeByte(image.pixels[x, y][1])
						writeByte(image.pixels[x, y][2])
					else:
						writeByte(0)
						writeByte(0)
						writeByte(0)

	else:
		# Perform gamma- and brightness-adjustment on pixel data
		sys.stdout.write(
		  "const uint8_t PROGMEM pixels%02d[] = {" % imgNum)
		numBytes = image.size[0] * numLEDs * 3

		for x in range(image.size[0]):
			for y in range(numLEDs):
				if y < image.size[1]:
					writeByte(int(pow((
					  image.pixels[x, y][0] / 255.0),
					  gamma) * bR1 + 0.5))
					writeByte(int(pow((
					  image.pixels[x, y][1] / 255.0),
					  gamma) * bG1 + 0.5))
					writeByte(int(pow((
					  image.pixels[x, y][2] / 255.0),
					  gamma) * bB1 + 0.5))
				else:
					writeByte(0)
					writeByte(0)
					writeByte(0)

	print " };" # end pixels[] array
	print

# Last pass, print table of images...

print "typedef struct {"
print "  uint8_t        type;    // PALETTE[1,4,8] or TRUECOLOR"
print "  line_t         lines;   // Length of image (in scanlines)"
print "  const uint8_t *palette; // -> PROGMEM color table (NULL if truecolor)"
print "  const uint8_t *pixels;  // -> Pixel data in PROGMEM"
print "} image;"
print
print "const image PROGMEM images[] = {"

for imgNum, image in enumerate(images): # For each image in list...
	sys.stdout.write("  { ")
	if image.numColors <= 2:
		sys.stdout.write("PALETTE1 , ")
	elif image.numColors <= 16:
		sys.stdout.write("PALETTE4 , ")
	elif image.numColors <= 256:
		sys.stdout.write("PALETTE8 , ")
	else:
		sys.stdout.write("TRUECOLOR, ")

	sys.stdout.write(" %3d, " % image.size[0])

	if image.numColors <= 256:
		sys.stdout.write("(const uint8_t *)palette%02d, " % imgNum)
	else:
		sys.stdout.write("NULL                      , ")

	sys.stdout.write("pixels%02d }" % imgNum)

	if imgNum < len(images) - 1:
		print(",")
	else:
		print

print "};"
print
print "#define NUM_IMAGES (sizeof(images) / sizeof(images[0]))"
