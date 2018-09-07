#!/usr/bin/python

# Image converter for 'Uncanny Eyes' project.  Generates tables for
# eyeData.h file.  Requires Python Imaging Library.  Expects six image
# files: sclera, iris, upper and lower eyelid map (symmetrical), upper
# and lower eyelif map (asymmetrical L/R) -- defaults will be used for
# each if not specified.  Also generates polar coordinate map for iris
# rendering (pass diameter -- must be an even value -- as 7th argument),
# pupil is assumed round unless pupilMap.png image is present.
# Output is to stdout; should be redirected to file for use.

# This is kinda some horrible copy-and-paste code right now for each of
# the images...could be improved, but basically does the thing.

import sys
import math
from PIL import Image

# Write hex digit (with some formatting for C array) to stdout
def outputHex(n, digits):
	global columns, column, counter, limit
	column += 1                        # Increment column number
	if column >= columns:              # If max column exceeded...
		sys.stdout.write("\n  ")   # end current line, start new one
		column = 0                 # Reset column number
	sys.stdout.write("{0:#0{1}X}".format(n, digits + 2))
	counter += 1                       # Increment element index
	if counter < limit:                # If NOT last element in list...
		sys.stdout.write(",")      # add column between elements
		if column < (columns - 1): # and space if not last column
			sys.stdout.write(" ")
	else:
		print(" };");              # Cap off table

# OPEN AND VALIDATE SCLERA IMAGE FILE --------------------------------------

try:    filename = sys.argv[1]
except: filename = "sclera.png"
im     = Image.open(filename)
im     = im.convert("RGB")
pixels = im.load()

# GENERATE SCLERA ARRAY ----------------------------------------------------

# Initialize outputHex() global counters:
counter = 0                       # Index of next element to generate
columns = 8                       # Number of columns in formatted output
column  = columns                 # Current column number in output
limit   = im.size[0] * im.size[1] # Total # of elements in generated list

print "#define SCLERA_WIDTH  " + str(im.size[0])
print "#define SCLERA_HEIGHT " + str(im.size[1])
print

sys.stdout.write("const uint16_t sclera[SCLERA_HEIGHT][SCLERA_WIDTH] = {")

# Convert 24-bit image to 16 bits:
for y in range(im.size[1]):
	for x in range(im.size[0]):
		p = pixels[x, y] # Pixel data (tuple)
		outputHex(((p[0] & 0b11111000) << 8) | # Convert 24-bit RGB
		          ((p[1] & 0b11111100) << 3) | # to 16-bit value w/
		          ( p[2] >> 3), 4)             # 5/6/5-bit packing

# OPEN AND VALIDATE IRIS IMAGE FILE ----------------------------------------

try:    filename = sys.argv[2]
except: filename = "iris.png"
im = Image.open(filename)
if (im.size[0] > 512) or (im.size[1] > 128):
	sys.stderr.write("Image can't exceed 512 pixels wide or 128 pixels tall")
	exit(1)
im     = im.convert("RGB")
pixels = im.load()

# GENERATE IRIS ARRAY ------------------------------------------------------

counter = 0 # Reset outputHex() counters again for new table
column  = columns
limit   = im.size[0] * im.size[1]

print
print "#define IRIS_MAP_WIDTH  " + str(im.size[0])
print "#define IRIS_MAP_HEIGHT " + str(im.size[1])
print

sys.stdout.write("const uint16_t iris[IRIS_MAP_HEIGHT][IRIS_MAP_WIDTH] = {")

for y in range(im.size[1]):
	for x in range(im.size[0]):
		p = pixels[x, y] # Pixel data (tuple)
		outputHex(((p[0] & 0b11111000) << 8) | # Convert 24-bit RGB
		          ((p[1] & 0b11111100) << 3) | # to 16-bit value w/
		          ( p[2] >> 3), 4)             # 5/6/5-bit packing

# OPEN AND VALIDATE UPPER EYELID THRESHOLD MAP (symmetrical) ---------------

try:    filename = sys.argv[3]
except: filename = "lid-upper-symmetrical.png"
im = Image.open(filename)
if (im.size[0] != 128) or (im.size[1] != 128):
	sys.stderr.write("Image size must match screen size")
	exit(1)
im     = im.convert("L")
pixels = im.load()

# GENERATE UPPER LID ARRAY (symmetrical) -----------------------------------

counter = 0
columns = 12
column  = columns
limit   = im.size[0] * im.size[1]

print
print "#define SCREEN_WIDTH  " + str(im.size[0])
print "#define SCREEN_HEIGHT " + str(im.size[1])
print
print "#ifdef SYMMETRICAL_EYELID"
print

sys.stdout.write("const uint8_t upper[SCREEN_HEIGHT][SCREEN_WIDTH] = {")

for y in range(im.size[1]):
	for x in range(im.size[0]):
		outputHex(pixels[x, y], 2) # 8-bit value per pixel

# OPEN AND VALIDATE LOWER EYELID THRESHOLD MAP (symmetrical) ---------------

try:    filename = sys.argv[4]
except: filename = "lid-lower-symmetrical.png"
im     = Image.open(filename)
if (im.size[0] != 128) or (im.size[1] != 128):
	sys.stderr.write("Image size must match screen size")
	exit(1)
im     = im.convert("L")
pixels = im.load()

# GENERATE LOWER LID ARRAY (symmetrical) -----------------------------------

counter = 0
column  = columns
limit   = im.size[0] * im.size[1]

print
sys.stdout.write("const uint8_t lower[SCREEN_HEIGHT][SCREEN_WIDTH] = {")

for y in range(im.size[1]):
	for x in range(im.size[0]):
		outputHex(pixels[x, y], 2) # 8-bit value per pixel

# OPEN AND VALIDATE UPPER EYELID THRESHOLD MAP (asymmetrical) --------------

try:    filename = sys.argv[5]
except: filename = "lid-upper.png"
im = Image.open(filename)
if (im.size[0] != 128) or (im.size[1] != 128):
	sys.stderr.write("Image size must match screen size")
	exit(1)
im     = im.convert("L")
pixels = im.load()

# GENERATE UPPER LID ARRAY (asymmetrical) ----------------------------------

counter = 0
column  = columns
limit   = im.size[0] * im.size[1]

print
print "#else"
print

sys.stdout.write("const uint8_t upper[SCREEN_HEIGHT][SCREEN_WIDTH] = {")

for y in range(im.size[1]):
	for x in range(im.size[0]):
		outputHex(pixels[x, y], 2) # 8-bit value per pixel

# OPEN AND VALIDATE LOWER EYELID THRESHOLD MAP (asymmetrical) --------------

try:    filename = sys.argv[6]
except: filename = "lid-lower.png"
im     = Image.open(filename)
if (im.size[0] != 128) or (im.size[1] != 128):
	sys.stderr.write("Image size must match screen size")
	exit(1)
im     = im.convert("L")
pixels = im.load()

# GENERATE LOWER LID ARRAY (asymmetrical) ----------------------------------

counter = 0
column  = columns
limit   = im.size[0] * im.size[1]

print
sys.stdout.write("const uint8_t lower[SCREEN_HEIGHT][SCREEN_WIDTH] = {")

for y in range(im.size[1]):
	for x in range(im.size[0]):
		outputHex(pixels[x, y], 2) # 8-bit value per pixel

# GENERATE POLAR COORDINATE TABLE ------------------------------------------

try:    irisSize = int(sys.argv[7])
except: irisSize = 80
if irisSize % 2 != 0:
	sys.stderr.write("Iris diameter must be even value")
	exit(1)
radius      = irisSize / 2
# For unusual-shaped pupils (dragon, goat, etc.), a precomputed image
# provides polar distances.  Optional 8th argument is filename (or file
# 'pupilMap.png' in the local directory) is what's used, otherwise a
# regular round iris is calculated.
try:    filename = sys.argv[8]
except: filename = "pupilMap.png"
usePupilMap = True
try:
	im     = Image.open(filename)
	if (im.size[0] != irisSize) or (im.size[1] != irisSize):
		sys.stderr.write("Image size must match iris size")
		exit(1)
	im     = im.convert("L")
	pixels = im.load()
except:
	usePupilMap = False

print
print "#endif // SYMMETRICAL_EYELID"
print
print "#define IRIS_WIDTH  " + str(irisSize)
print "#define IRIS_HEIGHT " + str(irisSize)

# One element per screen pixel, 16 bits per element -- high 9 bits are
# angle relative to center point (fixed point, 0-511) low 7 bits are
# distance from circle perimeter (fixed point, 0-127, pixels outsize circle
# are set to 127).

counter = 0
columns = 8
column  = columns
limit   = irisSize * irisSize

sys.stdout.write("\nconst uint16_t polar[%s][%s] = {" % (irisSize, irisSize))

for y in range(irisSize):
	dy = y - radius + 0.5
	for x in range(irisSize):
		dx       = x - radius + 0.5
		distance = math.sqrt(dx * dx + dy * dy)
		if(distance >= radius): # Outside circle
			outputHex(127, 4) # angle = 0, dist = 127
		else:
			if usePupilMap:
				# Look up polar coordinates in pupil map image
				angle     = math.atan2(dy, dx)  # -pi to +pi
				angle    += math.pi             # 0.0 to 2pi
				angle    /= (math.pi * 2.0)     # 0.0 to <1.0
				distance  = pixels[x, y] / 255.0
			else:
				angle     = math.atan2(dy, dx)  # -pi to +pi
				angle    += math.pi             # 0.0 to 2pi
				angle    /= (math.pi * 2.0)     # 0.0 to <1.0
				distance /= radius              # 0.0 to <1.0
			distance *= 128.0                 # 0.0 to <128.0
			if distance > 127: distance = 127 # Clip
			a         = int(angle * 512.0)    # 0 to 511
			d         = 127 - int(distance)   # 127 to 0
			outputHex((a << 7) | d, 4)

