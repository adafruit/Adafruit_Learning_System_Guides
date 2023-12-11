#!/bin/sh

# Fades/cycles the globe program through different scenes

# Show all files in the maps directory in alphabetical order
FILES=maps/*.jpg
# If you'd prefer a subset of files, different order or location,
# you can instead make a list of filenames, e.g.:
# FILES="
# maps/earth.jpg
# maps/moon.jpg
# maps/jupiter.jpg
# "

# Flags passed to globe program each time.
# --led-pwm-bits=9 because long chain is otherwise flickery (default is 11)
# -a 3 for 3x3 antialiasing (use 2 or 1 for slower Pi)
# -t 6 is run time in seconds before exiting
# -f 1 fades in/out for 1 second at either end
# Can add "-p" to this list if you want poles at cube vertices,
# or --led-rgb-sequence="BRG" with certain RGB matrices, etc.
set -- --led-pwm-bits=9 -a 3 -t 6 -f 1

while true; do
	for f in $FILES; do
		./globe $@ -i $f
	done
done
